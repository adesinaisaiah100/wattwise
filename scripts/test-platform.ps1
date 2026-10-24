param(
    [string]$BaseUrl = "http://127.0.0.1:5000",
    [string]$Email = "",
    [string]$Password = "",
    [switch]$TestModel
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$BaseUrl = $BaseUrl.TrimEnd("/")

function Invoke-ApiJson {
    param(
        [Microsoft.PowerShell.Commands.WebRequestSession]$Session,
        [string]$Method,
        [string]$Path,
        $Body = $null
    )
    $arguments = @{
        Uri = "$BaseUrl$Path"
        Method = $Method
        WebSession = $Session
        ContentType = "application/json"
    }
    if ($null -ne $Body) { $arguments.Body = ConvertTo-Json -InputObject $Body -Depth 30 }
    Invoke-RestMethod @arguments
}

function New-TestAccount {
    param([string]$AccountEmail, [string]$AccountPassword, [string]$DefaultMode)
    $webSession = New-Object Microsoft.PowerShell.Commands.WebRequestSession
    $created = $false
    try {
        $null = Invoke-ApiJson -Session $webSession -Method POST -Path "/api/auth/register" -Body @{
            email = $AccountEmail
            password = $AccountPassword
        }
        $created = $true
    } catch {
        $null = Invoke-ApiJson -Session $webSession -Method POST -Path "/api/auth/login" -Body @{
            email = $AccountEmail
            password = $AccountPassword
        }
    }
    $current = Invoke-ApiJson -Session $webSession -Method GET -Path "/api/auth/me"
    if (-not $current.data.user.preferred_mode) {
        $null = Invoke-ApiJson -Session $webSession -Method PUT -Path "/api/account/preferences" -Body @{ customer_type = $DefaultMode }
        $current = Invoke-ApiJson -Session $webSession -Method GET -Path "/api/auth/me"
    }
    [pscustomobject]@{
        Session = $webSession
        Email = $AccountEmail
        Password = $AccountPassword
        Mode = $current.data.user.preferred_mode
        Created = $created
    }
}

if ([string]::IsNullOrWhiteSpace($Email)) {
    $Email = "wattwise-smoke-$([DateTime]::UtcNow.ToString('yyyyMMddHHmmssfff'))@example.test"
}
if ([string]::IsNullOrWhiteSpace($Password)) { $Password = "WattWise-" + [Guid]::NewGuid().ToString("N") }

Write-Host "Checking the signed-in WattWise experience at $BaseUrl"
$health = Invoke-ApiJson -Session (New-Object Microsoft.PowerShell.Commands.WebRequestSession) -Method GET -Path "/api/health"
if (-not $health.success -or $health.data.calculation_engine -ne "ready") { throw "The API health check failed." }
Write-Host "PASS public health check; model state: $($health.data.model)"

$account = New-TestAccount -AccountEmail $Email -AccountPassword $Password -DefaultMode "prepaid"
$otherMode = if ($account.Mode -eq "prepaid") { "postpaid" } else { "prepaid" }
$otherEmail = "wattwise-isolation-$([Guid]::NewGuid().ToString('N'))@example.test"
$otherPassword = "WattWise-" + [Guid]::NewGuid().ToString("N")
$otherAccount = New-TestAccount -AccountEmail $otherEmail -AccountPassword $otherPassword -DefaultMode $otherMode

$prepaidAccount = if ($account.Mode -eq "prepaid") { $account } else { $otherAccount }
$postpaidAccount = if ($account.Mode -eq "postpaid") { $account } else { $otherAccount }
foreach ($pair in @(@{ Account = $prepaidAccount; Path = "/prepaid" }, @{ Account = $postpaidAccount; Path = "/postpaid" })) {
    $page = Invoke-WebRequest -Uri "$BaseUrl$($pair.Path)" -UseBasicParsing -WebSession $pair.Account.Session
    if ($page.StatusCode -ne 200) { throw "The signed-in page $($pair.Path) did not load." }
    Write-Host "PASS selected service page $($pair.Path)"
}
$accountPage = Invoke-WebRequest -Uri "$BaseUrl/account" -UseBasicParsing -WebSession $account.Session
if ($accountPage.StatusCode -ne 200) { throw "The signed-in household page did not load." }
Write-Host "PASS household account page"

$prepaid = Get-Content (Join-Path $root "phases/contracts/prepaid-request.example.json") -Raw | ConvertFrom-Json
$postpaid = Get-Content (Join-Path $root "phases/contracts/postpaid-request.example.json") -Raw | ConvertFrom-Json
$prepaidResult = Invoke-ApiJson -Session $prepaidAccount.Session -Method POST -Path "/api/prepaid/analyze" -Body $prepaid
$postpaidResult = Invoke-ApiJson -Session $postpaidAccount.Session -Method POST -Path "/api/postpaid/analyze" -Body $postpaid
if (-not $prepaidResult.success -or -not $prepaidResult.data.routine_options) { throw "Prepaid analysis did not return routine options." }
if (-not $postpaidResult.success -or -not $postpaidResult.data.billed_consumption) { throw "Postpaid analysis did not return bill comparison results." }
Write-Host "PASS prepaid plan: $($prepaidResult.data.estimated_daily_consumption_kwh) kWh/day"
Write-Host "PASS postpaid bill comparison: $($postpaidResult.data.estimated_household_kwh) estimated kWh"

$null = Invoke-ApiJson -Session $prepaidAccount.Session -Method PUT -Path "/api/account/appliances" -Body @{ appliances = $prepaid.appliances }
$null = Invoke-ApiJson -Session $prepaidAccount.Session -Method POST -Path "/api/account/history" -Body @{ mode = "prepaid"; case = $prepaid }
$null = Invoke-ApiJson -Session $postpaidAccount.Session -Method PUT -Path "/api/account/appliances" -Body @{ appliances = $postpaid.appliances }
$null = Invoke-ApiJson -Session $postpaidAccount.Session -Method POST -Path "/api/account/history" -Body @{ mode = "postpaid"; case = $postpaid }
Write-Host "PASS save each household's appliance list and analysis"

$null = Invoke-ApiJson -Session $account.Session -Method POST -Path "/api/auth/logout"
$null = Invoke-ApiJson -Session $account.Session -Method POST -Path "/api/auth/login" -Body @{ email = $Email; password = $Password }
$savedProfile = Invoke-ApiJson -Session $account.Session -Method GET -Path "/api/account/appliances"
$history = Invoke-ApiJson -Session $account.Session -Method GET -Path "/api/account/history?limit=100"
if ($savedProfile.data.appliances.Count -ne $prepaid.appliances.Count) { throw "The saved profile did not load after signing in again." }
if ($history.data.entries.Count -lt 1) { throw "The selected service analysis history did not load." }
Write-Host "PASS sign out, sign in, and retrieve saved household data"

if ($TestModel) {
    $aiCases = @(
        @{ Account = $prepaidAccount; Mode = "prepaid"; Case = $prepaid },
        @{ Account = $postpaidAccount; Mode = "postpaid"; Case = $postpaid }
    )
    foreach ($item in $aiCases) {
        $caseForPlan = $item.Case | ConvertTo-Json -Depth 30 | ConvertFrom-Json
        if ($item.Mode -eq "postpaid") {
            $caseForPlan | Add-Member -NotePropertyName target_reduction_percent -NotePropertyValue 20 -Force
        }
        $planResponse = Invoke-ApiJson -Session $item.Account.Session -Method POST -Path "/api/recommendations/plan" -Body @{
            mode = $item.Mode
            case = $caseForPlan
        }
        $plan = $planResponse.data.plan
        if (-not $planResponse.success -or -not $plan.schedule.Count -or $null -eq $plan.goal.achieved) {
            throw "The AI routine plan for $($item.Mode) did not return a verified schedule."
        }
        Write-Host "PASS Qwen $($item.Mode) plan ($($plan.model_proposal_rounds) model draft(s), goal met: $($plan.goal.achieved))"
    }

    $modelAccount = $prepaidAccount
    $modelCase = $prepaid
    $modelMode = "prepaid"
    if ($account.Mode -eq "postpaid") { $modelAccount = $postpaidAccount; $modelCase = $postpaid; $modelMode = "postpaid" }
    $stream = Invoke-WebRequest -Uri "$BaseUrl/api/recommendations/explain/stream" -Method POST -WebSession $modelAccount.Session -ContentType "application/json" -Body (ConvertTo-Json -Depth 30 -InputObject @{ mode = $modelMode; case = $modelCase }) -UseBasicParsing
    if ($stream.StatusCode -ne 200 -or $stream.Content -notmatch '"type"\s*:\s*"token"') { throw "The streamed explanation did not return model text." }
    Write-Host "PASS streamed local Qwen explanation"
} else {
    Write-Host "SKIP model text (rerun with -TestModel while llama.cpp is running)"
}

Write-Host ""
Write-Host "ALL SMOKE CHECKS PASSED."
Write-Host "Primary test account: $Email"
Write-Host "Primary test password: $Password"
Write-Host "This script creates two synthetic accounts in the running app's local database. Keep credentials private."

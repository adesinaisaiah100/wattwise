# WattWise demo walkthrough

Use synthetic values only. The examples below match the request fixtures in `phases/contracts/`; they are not a live customer's bill or an official tariff quote. Create separate local accounts for the prepaid and postpaid walkthroughs because an account selects one service type.

## Prepaid journey

1. Start Flask and the local Qwen server using the [README setup](../README.md#run-locally).
2. Register a demo account, select **Prepaid**, and add the sample appliances from `phases/contracts/prepaid-request.example.json`.
3. Use a 14-day target and 60 kWh currently showing on the meter. The fixture's appliance schedule estimates about **2.1 kWh/day** (about **29.4 kWh** over 14 days), leaving about **30.6 kWh** by the target date. At the same estimated daily use, 60 kWh would last about **28.6 days**. Results can vary with changed appliance details.
4. Generate an AI routine plan. Show the goal status, usual-versus-planned chart, schedule table, and model progress. Apply the suggested routine and recalculate to show how edited hours/days change the deterministic estimate.

## Postpaid journey

1. Register a second demo account and select **Postpaid**.
2. Add the appliances from `phases/contracts/postpaid-request.example.json`, set a 30-day bill period, and enter the sample readings 1000 and 1100 kWh (multiplier 1). The app derives **100 kWh billed**. The sample appliance schedule estimates **63 kWh** for the period.
3. Enter the sample ₦100/kWh tariff, ₦10,000 energy charge, ₦12,500 total amount due, and ₦2,500 other charges. The app should keep the estimate, billed units, estimated energy charge, and total due as separate values. The example tariff is synthetic and is not an official IBEDC tariff.
4. Generate a plan using the default or selected reduction goal. Show the chart/table and explain that the target applies to appliance-estimated use; it does not change the billed units or bill amount.

## Show behavior when Qwen is offline

Leave Flask running and stop the llama.cpp terminal with `Ctrl+C`. Refresh `/api/health`: the Flask app and calculation engine should remain ready while the model is `not_loaded`. Run a prepaid or postpaid analysis again to demonstrate that bill and meter calculations still work. AI plan generation and explanations should report model unavailability. Restart `scripts/start_model.ps1` or `scripts/start_model.sh` after the demo.

## Presentation notes

- Use sample fixture values or other invented values. Never display a real customer's bill, email, or account history in a recording.
- Point out estimate assumptions, user-entered versus typical appliance ratings, and the essential-appliance protection.
- Explain that Qwen returns a proposed schedule, while WattWise validates the IDs and routines and calculates kWh and charges in Python.
- Do not present WattWise as a DisCo integration, meter controller, receipt OCR, official bill audit, or fraud detector.
- Capture screenshots and a short backup video after the team has rehearsed this flow on the target demo computer. The model's proposed schedule is intentionally not hard-coded because its routine suggestions can vary between runs.

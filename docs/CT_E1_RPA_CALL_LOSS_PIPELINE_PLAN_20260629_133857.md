# CT-e1 RPA / Call Loss pipeline plan

## Conclusion

The CT-e1 external RPA and the existing Call Loss tasks are separate mechanisms and must be connected as a pipeline.

## Pipeline

External RPA -> data/ct_e1/inbox -> Call Loss processing

## Current PC interim operation

- Human prepares CT-e1 login/navigation/report condition screen.
- Human runs the RPA BAT manually.
- Scheduler is not useful on the current PC unless the condition screen is guaranteed to be ready.

## Separate PC target operation

- Keep CT-e1 logged in with the report condition screen visible/frontmost.
- Run RPA at cutoff time.
- Run Call Loss after enough completion margin.

## Adopted schedule design

- 18:00 RPA acquisition -> 18:10 Call Loss
- 20:00 RPA acquisition -> 20:10 Call Loss
- 21:00 RPA acquisition -> 21:10 Call Loss
- Optional: 19:00 RPA acquisition -> 19:10 Call Loss

## Accurate scope

This is not CT-e1 login-to-CSV fully unattended automation.
Accurate scope: report condition screen visible/frontmost -> output -> save -> inbox.

## Next implementation step

On the current PC, create a daily manual BAT that runs the known-good RPA.
On the separate PC, when setup time is available, register paired RPA and Call Loss scheduler tasks using the above times.

## Do not

- Do not modify V8 save code.
- Do not modify V9 output click code.
- Do not run Live just for reassurance.
- Do not attach or share multimulti_os.db.

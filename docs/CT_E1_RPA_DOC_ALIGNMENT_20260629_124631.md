# CT-e1 RPA documentation alignment

## Result

CLAUDE.md and AGENTS.md were updated to remove the contradiction between the repository rule and the external CT-e1 RPA reality.

## Updated files

- CLAUDE.md
- AGENTS.md

## External RPA pointer

C:\Users\User\Documents\Projects\multi-multi-os-local\ct_e1_export_rpa\_LATEST_CTE1_RPA_ADOPTION.md

## Boundary

- CT-e1 GUI automation is allowed only in multi-multi-os-local/ct_e1_export_rpa.
- multi-multi-os does not own the CT-e1 GUI RPA implementation.
- multi-multi-os consumes CSV from data/ct_e1/inbox.

## Accurate success wording

Confirmed: report condition screen visible/frontmost -> V9 output button auto-click -> V8 save -> inbox CSV saved.

Not confirmed: CT-e1 login-to-CSV fully unattended automation.

## DB handling

Do not include multimulti_os.db in handoff/review materials. DB files remain excluded from git and should not be shared as review artifacts.

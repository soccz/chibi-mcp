# Pilot Playbook

Use this playbook to learn whether chibi-mcp is commercially useful before adding monetization.

No paid plans, checkout, license keys, Sponsors tiers, paid packs, or paid random pulls are enabled by this playbook.

## Pilot Goals

The pilot should answer:

- Can a new user install it without maintainer help?
- Does the pet make AI coding sessions more memorable or shareable?
- Which client path works best: Claude Code, Codex, VS Code, or mixed?
- Do teams understand the no-telemetry/localhost trust position?
- Do creator/team packs feel valuable enough to request more?

## Pilot Segments

| Segment | Ask | Success signal |
|---|---|---|
| Individual Claude/Codex users | install, open pet, use gacha/options | they keep it installed after a few sessions |
| VS Code users | install `.vsix`, open sidebar, save/debug reaction | they understand the extension value quickly |
| Small teams | run audit, test team pack, report rollout blockers | they ask about admin rollout rather than basic purpose |
| Creators | submit a clean pack idea | pack passes rights metadata review |
| Partners | propose a free collab/drop | they bring a distribution channel |

## Intake

Use:

- `.github/ISSUE_TEMPLATE/team_pilot.yml`
- `.github/ISSUE_TEMPLATE/character_pack.yml`
- `.github/ISSUE_TEMPLATE/collaboration_idea.yml`
- `.github/ISSUE_TEMPLATE/showcase.yml`

Ask every pilot participant:

- OS and client path.
- Install command used.
- Whether `chibi-mcp --check` passed.
- First moment that felt useful or fun.
- First blocker or confusing step.
- Whether they would share a screenshot/GIF.
- Whether they would request a custom pack later.

## Metrics Without Telemetry

Track only user-submitted or public aggregate signals:

- GitHub stars;
- GitHub issues and discussions;
- GitHub Traffic views/clones/referrers;
- GitHub Release downloads;
- VSIX/Marketplace download counts if published later;
- user-submitted showcase screenshots;
- pack submissions that pass `chibi-pack validate --submission`.

Do not add hidden telemetry to measure pilots.

## Before Any Paid Decision

Do not decide pricing yet. First gather:

- install success rate by client/platform;
- number of repeat users;
- number of pack requests;
- number of team rollout blockers;
- recurring support questions;
- whether the demo GIF and README explain the value in under 10 seconds.

## Source Notes

- GitHub Traffic provides recent repository views, clones, referrers, and popular content: https://docs.github.com/en/repositories/viewing-activity-and-data-for-your-repository/viewing-traffic-to-a-repository
- GitHub issue forms standardize useful feedback from contributors and users: https://docs.github.com/en/communities/using-templates-to-encourage-useful-issues-and-pull-requests/configuring-issue-templates-for-your-repository
- VS Code Marketplace and `.vsix` distribution are documented in the VS Code extension publishing guide: https://code.visualstudio.com/api/working-with-extensions/publishing-extension

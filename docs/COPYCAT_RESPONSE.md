# Copycat and Rights Response

This is the response playbook when someone copies official artwork, submits risky images, or creates confusingly similar GitHub/marketplace assets. It is operational guidance, not legal advice.

## First Triage

Classify the problem before acting:

| Situation | Primary path |
|---|---|
| Official PNG, screenshot, README image, or social preview copied | copyright evidence and possible DMCA |
| Repo/package/listing pretends to be official | trademark, impersonation, or user-confusion report |
| Submitted pack uses third-party characters/logos/fan art | reject or request provenance |
| Fork keeps attribution and is clearly unofficial | normally allowed under code license |

## Evidence To Preserve

Before contacting anyone, collect:

- copied URL, repository, release, package, or marketplace listing;
- copied file path and commit SHA if available;
- official source file path and commit SHA;
- screenshots of the copied page and official page;
- hash or filename of copied image when useful;
- short comparison notes;
- author/contributor rights statement or permission record;
- date observed.

Use stable links where possible:

```bash
git rev-parse HEAD
git log --follow -- assets/social-preview.png
sha256sum assets/social-preview.png
```

## Friendly First Contact

When the issue looks accidental, ask for a fix before escalating:

```text
Hi. This appears to copy official chibi-mcp artwork or presentation in a way that may confuse users.

Please either:
1. remove the official assets,
2. add clear fork/unofficial labeling and attribution, or
3. provide the permission/provenance record for the artwork.

Original source:
<official repo file/commit>

Copied location:
<copied URL>
```

Keep the message factual. Do not threaten, argue ownership of broad ideas, or claim protection over the general concept of an AI coding pet.

## When To Escalate

Escalate if:

- official assets are copied without attribution or permission;
- the copy claims official status;
- package or marketplace names confuse users;
- a submitted pack contains third-party IP without permission;
- the maintainer refuses to remove or clarify the copied material.

Potential public platform paths:

- GitHub DMCA takedown for copyright claims.
- GitHub trademark policy for registered trademark misuse or confusing brand use.
- GitHub impersonation policy for accounts/projects pretending to be the official project.
- Marketplace-specific abuse/report forms for VS Code/Open VSX or other registries.

## Escalation Routing

Match the situation to the correct path — sending the wrong kind of notice (e.g. a DMCA against a legitimate fork) creates real risk (see below):

| What happened | Correct path | NOT this |
|---|---|---|
| Code copied, attribution kept, clearly unofficial | Allowed under MIT — no action | not DMCA |
| Code copied **and** claims to be official | GitHub impersonation / trademark report | not a copyright DMCA |
| Official PNG / screenshot / social preview copied bit-for-bit | DMCA takedown (template below) | — |
| Package/social-preview name causes user confusion | trademark + unfair-competition (Lanham §43(a)) report | not DMCA |
| Submitted pack contains third-party IP | reject via `chibi-pack validate --submission` + request provenance | not DMCA against the submitter's repo |

Always try **Friendly First Contact** before any platform report.

## DMCA Takedown Notice Template

Use this **only** for direct copying of official copyrighted assets (artwork, screenshots, social preview, exact text) — not for code reuse, which the MIT license permits. A valid 17 U.S.C. §512(c)(3) notice must include all six elements:

```text
1. Identification of the copyrighted work:
   chibi-mcp official asset at <repo path> (commit <SHA>, see ASSET_MANIFEST).
2. Identification and exact URL of the allegedly infringing material:
   <copied URL>
3. Contact information (name, email, address) of the reporter.
4. A statement that I have a good-faith belief that the use is not authorized
   by the copyright owner, its agent, or the law.
5. A statement that the information in this notice is accurate, and — under
   penalty of perjury — that I am the copyright owner or authorized to act
   on the owner's behalf.
6. Physical or electronic signature of the owner or authorized agent.
```

Submit via GitHub's DMCA process (copyright@github.com / the GitHub copyright claims form). Do **not** add "all rights reserved" boilerplate or claim ownership of broad ideas.

## Risks Of Sending A Notice

A takedown is not free of risk — read this before sending one:

- **Consider fair use first.** *Lenz v. Universal* (9th Cir. 2015) requires a good-faith fair-use evaluation before sending a DMCA notice. Forks, tutorials, reviews, and commentary may be fair use.
- **§512(f) liability.** Knowingly misrepresenting that material is infringing exposes the sender to damages and attorney's fees. Do not DMCA a legitimate fork or code reuse.
- **Counter-notice reality.** If the other party files a counter-notice, GitHub restores the content in ~10–14 business days unless the rights holder files a federal lawsuit. For a solo maintainer, litigation is usually impractical — so reserve DMCA for clear, direct asset copying and prefer Friendly First Contact everywhere else.

## What Not To Claim

Do not claim exclusive ownership over:

- the general idea of a local desktop pet;
- MCP integration as a concept;
- coding-session reactions as a broad feature idea;
- cute coding mascots in general;
- public domain facts, names, recipes, or generic UI patterns.

Focus on copied expression, official images, misleading brand presentation, exact text, package names, and user confusion.

## Pack Submission Response

If a pack lacks rights metadata:

```bash
chibi-pack validate --submission ./submitted-pack
```

Request these top-level `meta.json` fields:

```json
{
  "license": "original-submission",
  "source_rights": "Original artwork by <name>, submitted with permission for chibi-mcp review.",
  "rights_owner": "<name or organization>",
  "asset_origin": "original",
  "permission_scope": "May be reviewed, previewed, and distributed by chibi-mcp if accepted.",
  "no_third_party_ip": true
}
```

Reject or pause review for:

- third-party characters, mascots, logos, UI screenshots, or brand marks without written permission;
- AI-generated images that imitate a named living artist, studio, mascot, or copyrighted character;
- missing owner/permission scope;
- vague claims like `found online`, `inspired by <known character>`, `fan art`, or `free image`.

## References

- GitHub DMCA takedown policy: https://docs.github.com/github/site-policy/dmca-takedown-policy
- GitHub trademark policy: https://docs.github.com/github/site-policy/github-trademark-policy
- GitHub impersonation policy: https://docs.github.com/en/site-policy/acceptable-use-policies/github-impersonation
- U.S. Copyright Office FAQ: https://www.copyright.gov/help/faq/faq-general.html
- Creative Commons license overview: https://creativecommons.org/share-your-work/use-remix/cc-licenses/

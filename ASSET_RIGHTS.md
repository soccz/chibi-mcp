# Asset Rights and Provenance

This file records the current rights posture for project images, character
identity, and submitted character/option packs. It is an operational policy for
the repository, not legal advice.

## Current Scope

- Project code remains licensed under [MIT](LICENSE).
- Official artwork and project presentation are governed by
  [OFFICIAL_ASSET_TERMS.md](OFFICIAL_ASSET_TERMS.md), not treated as standalone
  stock art under the code license.
- Brand and naming confusion is covered by [TRADEMARK.md](TRADEMARK.md).
- The names `chibi-mcp` and `chibi`, the project social preview, starter
  character identity, and official pack presentation should not be used to
  imply sponsorship, endorsement, or an official release from this project.
- Character/option pack submissions must include `license`, `source_rights`,
  `rights_owner`, `asset_origin`, `permission_scope`, and
  `no_third_party_ip: true` before they are accepted for public review.
- Do not submit third-party copyrighted characters, mascots, logos, brand marks,
  screenshots, or fan-art unless you can provide permission.
- The four base modes and included free starter assets remain free. This policy
  does not add paid gates, license keys, checkout, Sponsors tiers, or team
  pricing.

## Provenance Table

| Path | Current provenance | Review rule |
|---|---|---|
| `assets/` | Project-generated starter characters, option layers, and launch images | Keep mirrored with packaged assets; no third-party brands or characters |
| `server/chibi_mcp/assets/` | Packaged copy of the project starter asset catalog | Same catalog and rights metadata as `assets/` |
| `vscode-ext/resources/` | VS Code extension copy of the project starter asset catalog | Same catalog and rights metadata as `assets/` |
| `docs/demo.gif`, `docs/screenshots/` | Generated demo, share-card, and showcase assets from the local project catalog | Regenerate from project assets only |
| `examples/packs/` | Sample-only creator/team packs generated for this repository | Must pass `chibi-pack validate --submission` |

## Pack Metadata Required For Public Submission

Every submitted `meta.json` should include top-level rights fields:

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

Use:

```bash
chibi-pack validate --submission ./my-pack
```

Normal local validation stays permissive so people can prototype quickly, but
submission validation fails if rights metadata is missing.

## If A Copy Or Infringing Pack Appears

Collect evidence before acting:

- URL, commit SHA, release asset, package name, or marketplace listing.
- The original project file path and commit where the asset first appeared.
- A short comparison showing the copied image, brand mark, or misleading
  official-endorsement claim.
- The rights basis: original project asset, commissioned file, contributor
  statement, or documented permission.

Use [docs/COPYCAT_RESPONSE.md](docs/COPYCAT_RESPONSE.md) to collect evidence
before acting. GitHub documents a DMCA process for copyright complaints and
counter-notices:
https://docs.github.com/github/site-policy/dmca-takedown-policy

For brand-name or logo protection, trademark registration is a separate business
decision. GitHub also documents trademark complaints, and USPTO explains that
trademarks typically cover brand names and logos used for goods or services:
https://docs.github.com/github/site-policy/github-trademark-policy
https://www.uspto.gov/trademarks/basics/trademark-process

## Decisions Not Yet Made

These should remain explicit user/business decisions:

- Whether to register `chibi-mcp`, `chibi`, or a logo as a trademark.
- Whether to keep high-resolution source art private and publish only runtime
  PNGs.
- Whether to allow commercial redistribution of official starter art.
- Whether to use a Creative Commons license for public asset packs.

Official references:

- U.S. Copyright Office: copyright protects original expression, but not facts,
  ideas, systems, or methods of operation:
  https://copyright.gov/help/faq/faq-protect.html
- USPTO trademark basics:
  https://www.uspto.gov/trademarks/basics
- Creative Commons license overview:
  https://creativecommons.org/share-your-work/use-remix/cc-licenses/

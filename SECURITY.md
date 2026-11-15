<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->
# Security and Safety Reporting

No OCE-CTL-01 software or hardware is released for operation. Even so, defects in future sensing, command arbitration, safety-chain logic, update tooling, documentation, or manufacturing records could have physical consequences.

## Report privately

Use the repository host’s private vulnerability reporting or private maintainer contact **if and where enabled**. Do not open a public issue for an exploitable vulnerability, credentials, personal data, or an unmitigated hazardous condition. Availability of a private channel must be checked in the actual hosting project; this document does not claim it is configured.

Include the affected revision/file, preconditions, impact, a non-destructive reproduction, and suggested containment. Remove secrets and identifying site/personnel data. Do not test against equipment, controllers, batteries, charging infrastructure, other people’s systems, or a live worksite.

## Expected handling

A maintainer should acknowledge reproducible reports, assess safety and security impacts together, limit disclosure until mitigation is available, credit reporters with consent, and record the resolution. Response-time guarantees are not made by this volunteer project. Coordinate disclosure before publication.

## Physical safety

For an immediate machinery hazard, stop only if it is safe and authorized, establish the site’s emergency controls, and contact responsible local/site personnel or emergency services. Repository maintainers are not an emergency response service. Do not defeat interlocks or attempt hazardous troubleshooting to gather a report.

## Supply chain and provenance

Do not add dependencies, remote scripts, executable models, signed artifacts, or controller images merely to demonstrate a fix. A future software phase will define supported versions and release identity. Until then, all content is prerelease concept material.

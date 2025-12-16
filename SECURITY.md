# Security Policy

## Supported Versions

We release patches for security vulnerabilities. Which versions are eligible for receiving such patches depends on the CVSS v3.0 Rating:

| CVSS v3.0 | Supported Versions                        |
| --------- | ------------------------------------------ |
| 9.0-10.0  | Releases within the previous three months |
| 4.0-8.9   | Most recent release                       |

## Reporting a Vulnerability

Please report (suspected) security vulnerabilities by creating a private security advisory on GitHub or by emailing the repository maintainer. You will receive a response within 48 hours. If the issue is confirmed, we will release a patch as soon as possible depending on complexity.

Please include the following information in your report:

- Type of issue (e.g. encryption bypass, path traversal, command injection, etc.)
- Full paths of source file(s) related to the manifestation of the issue
- The location of the affected source code (tag/branch/commit or direct URL)
- Any special configuration required to reproduce the issue
- Step-by-step instructions to reproduce the issue
- Proof-of-concept or exploit code (if possible)
- Impact of the issue, including how an attacker might exploit the issue

This information will help us triage your report more quickly.

## Security Considerations

GPGNotes is designed with security in mind, but users should be aware of the following:

### Encryption
- All notes are encrypted with GPG using your selected key
- The security of your notes depends on the strength of your GPG passphrase
- Encryption keys are managed by GPG, not by GPGNotes

### Local Storage
- Encrypted notes are stored in `~/.gpgnotes/notes/`
- Configuration (including GPG key ID but NOT the key itself) is stored in `~/.gpgnotes/config.json`
- Search index is unencrypted in `~/.gpgnotes/notes.db` (contains note IDs and metadata, not content)

### Git Synchronization
- Git sync is optional and disabled by default
- Use private repositories for syncing encrypted notes
- Encrypted notes are safe to store in version control
- Ensure your Git remote uses secure authentication (SSH keys or tokens)

### Best Practices
- Use a strong GPG passphrase
- Regularly backup your GPG private key securely
- Use private Git repositories for sync
- Keep your system and GPG software updated
- Review file permissions on `~/.gpgnotes/` directory

## Preferred Languages

We prefer all communications to be in English.

## Policy

We follow the principle of Coordinated Vulnerability Disclosure.

# Security and privacy

[English](SECURITY.md) · [Italiano](SECURITY.it.md)

Do not include Tapo passwords, MCP Bearer tokens, backup files or device/network identifiers in public issues. Crop or redact screenshots.

Smartlight stores Tapo credentials using the operating system credential store. Configuration backups omit those credentials, but can still contain device addresses, room names and schedules.

MCP is local by default. The optional LAN HTTP endpoint uses a Bearer token without transport encryption: use it only on a trusted network. Regenerate the token if it is exposed.

Mystic Light is an experimental Windows fallback. Automatic SDK acquisition requires detection of both MSI hardware and the required MSI software. Smartlight retrieves the pinned official MSI archive over HTTPS, verifies its SHA-256, and validates DLL architecture and required exports before a worker probes actual zones. The SDK is cached locally and is not redistributed in Smartlight packages. A subprocess limits crashes and hangs; it is not a sandbox for untrusted native code. Vendor software installation and any required elevated prompts remain part of the official vendor flow. Follow the MSI SDK license and do not substitute files from unknown sources.

No private reporting address is configured yet. Until the public repository provides a private security channel, do not publish working exploits or secrets in an issue.

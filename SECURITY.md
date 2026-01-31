# Security

## Reporting Issues

Found a security problem? Please [open a GitHub issue](../../issues/new) with details, or submit a pull request with a fix. For sensitive security issues, you can use GitHub's private vulnerability reporting feature.

## How we handle keys

- Private keys are generated client-side only
- We never see or store your private keys
- Keys stay on your device unless you export them
- HSM support for enterprise (AWS CloudHSM, Azure Key Vault)

## Crypto

- **Signatures**: Ed25519 (same as SSH, Signal)
- **Hashing**: SHA-256
- **TLS**: 1.2+ required

## Infrastructure

- All API traffic encrypted
- Rate limiting on all endpoints
- Input validation with Pydantic
- Optional blockchain anchoring for immutability

## Known Limitations

- Browser extension storage isn't encrypted (use for testing only)
- IPFS pinning requires external service
- No key recovery (by design - you own it)

## Contributing

Found something to improve? [Open a pull request](../../pulls) or [create an issue](../../issues/new).
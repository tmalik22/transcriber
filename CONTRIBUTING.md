# Contributing to Transcriber

Thank you for your interest in contributing to the Always-On Transcription Service! This document provides guidelines for contributing to the project.

## 🤝 How to Contribute

### Reporting Issues
- Use the GitHub issue tracker
- Provide detailed descriptions of bugs or feature requests
- Include system information (macOS version, hardware specs)
- Attach relevant log files (with personal information removed)

### Feature Requests
- Check existing issues to avoid duplicates
- Clearly describe the use case and expected behavior
- Consider the privacy-first, local-processing goals of the project

### Pull Requests
1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Test thoroughly on macOS
5. Update documentation as needed
6. Commit with clear, descriptive messages
7. Push to your fork
8. Open a pull request

## 🧪 Testing

Before submitting:
- Run `./demo.sh` to verify basic functionality
- Test with various meeting applications
- Ensure privacy and security standards are maintained

## 📋 Code Style

### Shell Scripts
- Use `set -euo pipefail` for error handling
- Include clear comments and logging
- Follow existing naming conventions

### Python Scripts
- Follow PEP 8 style guidelines
- Include type hints where appropriate
- Add comprehensive error handling
- Document functions with docstrings

## 🔒 Privacy Guidelines

This project prioritizes user privacy:
- All processing must remain local
- No data should be sent to external services (except optional calendar integration)
- Personal information must never be included in commits
- Audio recordings and transcripts should never be committed to the repository

## 📁 Project Structure

When adding new features:
- Scripts go in `scripts/`
- Configuration templates in `config/`
- Documentation updates in relevant markdown files
- Keep the modular architecture

## 🐛 Debugging

When reporting issues:
- Check log files in `logs/` directory
- Run individual scripts with verbose output
- Test with minimal configuration first

## 📝 Documentation

- Update README.md for major features
- Keep QUICKSTART.md current with setup process
- Add inline comments for complex logic
- Update configuration examples

## 🎯 Goals

Keep these project goals in mind:
- **Privacy-first**: All processing stays on-device
- **Zero-cost**: No cloud dependencies or subscriptions
- **Always-on**: Reliable, unattended operation
- **Cross-app**: Works with any meeting platform
- **Production-ready**: Robust error handling and monitoring

## 💬 Communication

- Use GitHub issues for technical discussions
- Keep discussions focused on improving the software
- Be respectful and constructive in feedback

## 📄 License

By contributing, you agree that your contributions will be licensed under the MIT License.

---

Thank you for helping make meeting transcription more accessible and private! 🎙️

# 📁 Project Organization Guide

This document describes the new organized structure of the PII/PCI Data Redaction Gateway after modularization.

## 📂 Directory Structure

```
data_redaction_gateway/
├── 📁 src/                           # Main source code (modular architecture)
│   ├── 📁 api/                       # FastAPI application layer
│   ├── 📁 cli/                       # Command-line interface
│   ├── 📁 config/                    # Configuration management
│   ├── 📁 core/                      # Core models and exceptions
│   ├── 📁 engines/                   # Redaction detection engines
│   ├── 📁 judge/                     # LLM-as-judge validation
│   ├── 📁 observability/             # Metrics and tracing
│   ├── 📁 policy/                    # Policy rule management
│   └── 📁 security/                  # Authentication and encryption
├── 📁 config/                        # Configuration files
├── 📁 docs/                          # Documentation (organized)
│   ├── 📁 configuration/             # Configuration guides
│   ├── 📁 llm_judge/                 # LLM judge documentation
│   └── 📁 setup/                     # Setup and troubleshooting
├── 📁 input/                         # Test input files
├── 📁 output/                        # Generated output files
├── 📁 tests/                         # Test suites (organized)
│   ├── 📁 integration/               # Integration tests
│   ├── 📁 scripts/                   # PowerShell test scripts
│   └── 📁 unit/                      # Unit tests
├── 📁 utils/                         # Utility scripts
├── main_modular.py                   # Main entry point (FastAPI)
├── cli_modular.py                    # CLI entry point
└── migration_guide.py               # Migration assistance
```

## 🚀 Quick Start

### Running the API Server
```bash
# Using the main entry point
python main_modular.py

# Using the CLI
python cli_modular.py serve
```

### Using the CLI
```bash
# Validate configuration
python cli_modular.py validate

# Dry-run redaction
python cli_modular.py dryrun input/test_transaction.json

# Check service health
python cli_modular.py health
```

### Running Tests
```bash
# Run all tests
python tests/run_tests.py

# Run specific test suites
python tests/integration/test_modular_functionality.py

# Run PowerShell test scripts
./tests/scripts/test_fastapi_endpoint.ps1
```

## 📚 Documentation

- **Configuration**: `docs/configuration/` - YAML config guides
- **LLM Judge**: `docs/llm_judge/` - LLM-as-judge setup and usage
- **Setup**: `docs/setup/` - Installation, troubleshooting, usage guides

## 🧪 Testing

- **Unit Tests**: `tests/unit/` - Component-level tests
- **Integration Tests**: `tests/integration/` - End-to-end functionality tests  
- **Test Scripts**: `tests/scripts/` - PowerShell automation scripts

## 📦 Modules Overview

### Core Architecture (`src/`)
- **api/**: FastAPI routers, middleware, application factory
- **config/**: Settings, validation, environment loading
- **core/**: Data models, exceptions, base classes
- **engines/**: Pluggable redaction detection (Regex, Luhn, NER)

### Advanced Features (`src/`)
- **judge/**: LLM-powered redaction validation
- **observability/**: Metrics collection, OpenTelemetry tracing
- **policy/**: YAML-based rule management
- **security/**: API authentication, encryption, sanitization

## 🔄 Migration Notes

Old monolithic files have been migrated to the new modular structure:
- `main.py` → `src/api/main.py`
- `models.py` → `src/core/models/`
- `config_loader.py` → `src/config/loader.py`
- `redaction_engine.py` → `src/engines/`
- And more...

The `compat.py` and `migration_guide.py` files assist with any remaining migration needs.

## ✨ Benefits

- **Modularity**: Clear separation of concerns
- **Testability**: Isolated components with focused tests  
- **Maintainability**: Smaller, focused modules
- **Extensibility**: Plugin architecture for new engines
- **Documentation**: Organized guides for each component
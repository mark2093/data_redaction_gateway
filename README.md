# Runtime PII/PCI Data Redaction Gateway

## Overview
This project implements a real-time data redaction gateway designed to identify and redact Personally Identifiable Information (PII) and Payment Card Industry (PCI) sensitive data from streaming data sources. The solution ensures data security and compliance by applying configurable redaction rules to multiple data formats.

## Problem Statement
Organizations need to protect sensitive PII/PCI data in real-time streaming scenarios while maintaining data utility for downstream processing. This gateway intercepts data streams, identifies sensitive information using configurable rules, and redacts it before forwarding to consumers.

## Project Structure
```
data_redaction_gateway/
├── input/                          # Input specifications and sample data
│   ├── problem_statement.md        # Detailed problem statement
│   ├── sample_input_data.json      # Sample JSON input data
│   ├── sample_output_data.json     # Expected output after redaction
│   └── redaction_rules.yaml        # YAML configuration for redaction rules
├── src/                            # Source code
│   ├── __init__.py
│   ├── redaction_engine.py         # Core redaction logic
│   ├── stream_processor.py         # Stream processing components
│   └── rule_parser.py              # YAML rule parser
├── utils/                          # Utility scripts
│   ├── __init__.py
│   └── data_stream_simulator.py    # Simulates real-time data streaming
├── config/                         # Configuration files
│   └── config.yaml                 # Application configuration
├── tests/                          # Unit and integration tests
│   ├── __init__.py
│   └── test_redaction.py
├── output/                         # Output directory for redacted data
├── requirements.txt                # Python dependencies
├── .gitignore                      # Git ignore rules
├── conversation.log                # Development conversation log
└── README.md                       # This file
```

## Approach

### 1. Data Ingestion
- Support for multiple source types (2 JSON sources, 1 text source)
- Real-time data stream simulation from static files
- Configurable data source connectors

### 2. Rule-Based Redaction
- YAML-based rule configuration for flexibility
- Pattern matching for PII/PCI data identification:
  - Credit card numbers
  - Social Security Numbers (SSN)
  - Email addresses
  - Phone numbers
  - Names and addresses
  - Custom patterns
- Multiple redaction strategies:
  - Full masking (e.g., `***********`)
  - Partial masking (e.g., `XXX-XX-1234`)
  - Hashing
  - Tokenization

### 3. Processing Pipeline
- Stream-based processing for efficiency
- Non-blocking architecture
- Error handling and logging
- Performance monitoring

### 4. Output Generation
- Redacted data output in original format
- Audit trail for compliance
- Metrics and reporting

## Dependencies

### Core Dependencies
```
python>=3.8
pyyaml>=6.0
jsonschema>=4.0
regex>=2023.0
```

### Streaming Dependencies
```
asyncio
aiofiles
```

### Testing Dependencies
```
pytest>=7.0
pytest-asyncio>=0.21
pytest-cov>=4.0
```

### Optional Dependencies
```
pandas>=2.0          # For data manipulation
kafka-python>=2.0    # For Kafka integration (future)
redis>=4.0           # For caching (future)
```

## Installation

### 1. Clone the Repository
```bash
git clone <repository-url>
cd data_redaction_gateway
```

### 2. Create Virtual Environment
```bash
python -m venv venv
# Windows
venv\Scripts\activate
# Linux/Mac
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

## Configuration

### Redaction Rules (redaction_rules.yaml)
Define redaction rules in YAML format:
```yaml
rules:
  - name: credit_card
    pattern: '\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b'
    redaction_type: partial
    keep_last: 4
  
  - name: ssn
    pattern: '\b\d{3}-\d{2}-\d{4}\b'
    redaction_type: full
  
  - name: email
    pattern: '[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
    redaction_type: hash
```

## Execution Steps

### Phase 1: Setup (Current)
1. ✅ Project structure created
2. ⏳ Awaiting input files from user:
   - Problem statement details
   - Sample input data
   - Sample output data
   - Redaction rules configuration

### Phase 2: Data Stream Simulator
Once sample source files are provided:
```bash
python utils/data_stream_simulator.py --source input/sample_input_data.json --interval 1
```

### Phase 3: Core Implementation
```bash
# Run the redaction gateway
python src/main.py --config config/config.yaml

# Run with streaming simulation
python src/main.py --config config/config.yaml --simulate-stream
```

### Phase 4: Testing
```bash
# Run all tests
pytest tests/

# Run with coverage
pytest tests/ --cov=src --cov-report=html
```

## Usage Examples

### Example 1: Process JSON Stream
```python
from src.redaction_engine import RedactionEngine
from src.stream_processor import StreamProcessor

# Initialize engine with rules
engine = RedactionEngine('input/redaction_rules.yaml')

# Process data
processor = StreamProcessor(engine)
processor.process_stream('input/sample_input_data.json')
```

### Example 2: Simulate Real-Time Stream
```python
from utils.data_stream_simulator import DataStreamSimulator

# Simulate streaming from static file
simulator = DataStreamSimulator(
    source_files=['input/source1.json', 'input/source2.json', 'input/source3.txt'],
    interval=0.5  # 500ms between records
)
simulator.start()
```

## Development Guidelines

### Code Standards
- Follow PEP 8 style guide
- Use type hints for function signatures
- Document all public APIs with docstrings
- Maintain test coverage above 80%

### Git Workflow
- Create feature branches for new functionality
- Write descriptive commit messages
- Update conversation.log with significant changes

## Performance Considerations
- Stream processing to handle large datasets
- Efficient regex compilation and caching
- Asynchronous I/O for non-blocking operations
- Configurable batch sizes for throughput optimization

## Security Notes
- Rules are loaded from trusted YAML files only
- No sensitive data is logged
- Audit trail maintains metadata only
- Output files have restricted permissions

## Future Enhancements
- [ ] Support for Apache Kafka integration
- [ ] Real-time dashboard for monitoring
- [ ] ML-based PII detection
- [ ] REST API for rule management
- [ ] Distributed processing support
- [ ] Cloud deployment configurations

## Contributing
This is a hackathon project. Development conversation is tracked in `conversation.log`.

## License
TBD

## Contact
Project developed for hackathon challenge: Runtime PII/PCI Data Redaction Gateway

---
**Status**: Initial Setup Complete - Awaiting Input Files
**Last Updated**: November 8, 2025

# Test Suite Documentation

This document describes the comprehensive test suite for GitHub Inventory, including the new integration tests and performance tests added to improve overall test coverage.

## Test Structure

### Original Tests (Unit Tests)
- `test_cli.py` - CLI argument parsing and environment variable loading
- `test_inventory.py` - GitHub CLI command execution and data processing (heavily mocked)
- `test_limit.py` - Limit parameter functionality
- `test_report.py` - Markdown report generation and CSV data reading
- `test_yaml_config.py` - YAML/JSON configuration parsing and validation

### New Integration and Performance Tests

#### Integration Tests (`test_integration.py`)
- **Purpose**: Test complete workflows using realistic GitHub CLI responses
- **Key Features**:
  - Realistic GitHub API response fixtures
  - End-to-end data collection workflows
  - Integration with actual GitHub CLI command patterns
  - Data consistency verification through the entire pipeline
  - Null value and edge case handling

#### End-to-End CLI Tests (`test_cli_e2e.py`)
- **Purpose**: Test complete CLI workflows with temporary directories
- **Key Features**:
  - Full CLI command simulation with temporary workspaces
  - File system integration testing
  - Multi-mode testing (owned-only, starred-only, report-only, batch)
  - Directory creation and file output verification
  - Performance testing with large datasets

#### Error Path Tests (`test_error_paths.py`)
- **Purpose**: Comprehensive error handling and failure scenario testing
- **Key Features**:
  - GitHub CLI authentication errors
  - API rate limiting and network failures
  - Malformed data handling
  - File permission and disk space errors
  - Unicode and special character handling
  - Memory pressure simulation

#### Performance Tests (`test_performance.py`)
- **Purpose**: Performance characteristics and stress testing
- **Key Features**:
  - Large dataset processing (100-1000+ repositories)
  - Memory efficiency testing
  - Concurrent processing simulation
  - File I/O performance benchmarks
  - Report generation with complex data

#### Batch Processing Tests (`test_batch_integration.py`)
- **Purpose**: Complete batch processing workflow testing
- **Key Features**:
  - Multi-user configuration processing
  - Custom YAML configuration handling
  - Error handling across multiple accounts
  - Directory structure management
  - Mixed limit configuration testing

### Test Fixtures (`fixtures/`)
- `github_responses.py` - Realistic GitHub CLI response data
  - Sample owned and starred repository responses
  - Branch count responses with error simulation
  - Large dataset generators for performance testing
  - Error response patterns for various failure scenarios

## Running the Tests

### All Tests
```bash
# Run all tests
make test
# or
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=github_inventory --cov-report=html --cov-report=term
```

### Test Categories
```bash
# Integration tests only
pytest tests/test_integration.py -v

# End-to-end CLI tests
pytest tests/test_cli_e2e.py -v

# Error path tests
pytest tests/test_error_paths.py -v

# Performance tests
pytest tests/test_performance.py -v

# Batch processing tests
pytest tests/test_batch_integration.py -v
```

### Markers
```bash
# Run by test type (when markers are added)
pytest -m integration
pytest -m performance
pytest -m error_paths
```

## Test Coverage Improvements

### Before (Original Tests)
- **Coverage Type**: Unit tests with heavy mocking
- **GitHub CLI Integration**: Fully mocked subprocess calls
- **Error Scenarios**: Limited error path coverage
- **File Operations**: Basic CSV testing with temp files
- **Performance**: No performance testing
- **Batch Processing**: Configuration parsing only

### After (Enhanced Test Suite)
- **Coverage Type**: Unit + Integration + E2E + Performance
- **GitHub CLI Integration**: Realistic response simulation
- **Error Scenarios**: Comprehensive error path testing
- **File Operations**: Full file system integration testing
- **Performance**: Large dataset and stress testing
- **Batch Processing**: Complete workflow integration testing

## Key Testing Strategies

### 1. Realistic Data Simulation
- GitHub API responses based on real API structure
- Edge cases: null values, empty responses, malformed data
- Large dataset generation for performance testing

### 2. Temporary File System Testing
- Each test gets isolated temporary directories
- File creation, reading, and cleanup verification
- Permission and disk space error simulation

### 3. Error Scenario Coverage
- Authentication failures
- Network connectivity issues  
- API rate limiting
- Malformed JSON responses
- File system errors
- Memory pressure scenarios

### 4. Performance Benchmarking
- Processing time assertions for large datasets
- Memory usage pattern verification
- Concurrent operation testing
- File I/O performance validation

### 5. Integration Workflow Testing
- Complete data flow from GitHub CLI to CSV/report output
- Multi-user batch processing workflows
- Configuration-driven execution paths
- Real-world usage scenario simulation

## Test Data and Fixtures

### Sample Repository Data
- **Owned repositories**: Mix of public/private, original/fork, various languages
- **Starred repositories**: Mix of popular projects with realistic metadata
- **Edge cases**: Null descriptions, missing languages, archived repos

### Large Dataset Generation
- Configurable dataset sizes (10-1000+ repositories)
- Realistic data distribution patterns
- Performance testing data with controlled characteristics

### Error Response Simulation
- Authentication required errors
- Rate limiting responses
- Network connectivity failures
- Repository not found scenarios

## Continuous Integration Considerations

### Test Execution Time
- Unit tests: < 10 seconds
- Integration tests: < 30 seconds
- Performance tests: < 60 seconds (with reasonable limits)
- Full suite: < 2 minutes

### Resource Requirements
- Temporary disk space for file operations
- Memory for large dataset testing
- No external network dependencies (all mocked)

### Test Isolation
- Each test uses isolated temporary directories
- No shared state between tests
- Proper cleanup of resources

## Future Test Enhancements

### Potential Additions
- Fuzzing tests for malformed input handling
- Property-based testing for data transformation logic
- Load testing for very large repositories (10k+ repos)
- Cross-platform file system testing
- GitHub CLI version compatibility testing

### Monitoring and Metrics
- Test execution time tracking
- Memory usage profiling
- Coverage trend monitoring
- Performance regression detection
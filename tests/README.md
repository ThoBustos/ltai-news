# Testing Guide

This directory contains unit and integration tests for the LTAI News project.

## Test Structure

```
tests/
├── unit/                    # Unit tests with mocked API responses
│   └── test_google_oauth.py
├── integration/            # Integration tests with real YouTube API
│   └── test_youtube_api.py
├── fixtures/               # Mock data for unit tests
│   └── youtube_responses.py
└── conftest.py            # Pytest configuration and fixtures
```

## Running Tests

### Install Dependencies

```bash
uv sync --dev
```

### Run All Tests

```bash
uv run python -m pytest
```

### Run Only Unit Tests

```bash
uv run python -m pytest tests/unit/
```

### Run Only Integration Tests

```bash
uv run python -m pytest tests/integration/
```

### Skip Integration Tests (Fast)

```bash
uv run python -m pytest -m "not integration"
```

### Run Specific Test File

```bash
uv run python -m pytest tests/integration/test_youtube_api.py
```

### Run with Verbose Output

```bash
uv run python -m pytest -v
```

### See API Responses (Debug Mode)

To see detailed API responses and logged data during integration tests:

```bash
# Enable debug logging
DEBUG_TESTS=1 uv run python -m pytest tests/integration/ -v -s

# Or use pytest's logging
uv run python -m pytest tests/integration/ -v -s --log-cli-level=DEBUG
```

This will show:
- Full API response JSON
- Channel metadata
- Video metadata
- All logged information

## Test Types

### Unit Tests (`tests/unit/`)

- **Fast**: Use mocked API responses
- **Isolated**: No external dependencies
- **Purpose**: Test logic, data parsing, error handling

**Example:**
```python
def test_search_channel_found(client, mock_youtube_service):
    # Mock API response
    # Test search_channel() logic
    # Assert results
```

### Integration Tests (`tests/integration/`)

- **Slower**: Use real YouTube API
- **Real Data**: Test with actual channels (e.g., Latent Space)
- **Purpose**: Verify API integration, data completeness, date filtering

**Requirements:**
- `GOOGLE_CREDENTIALS_JSON_PATH` must be set in `.env`
- Will use/create `test_token.json` for OAuth

**Example:**
```python
def test_get_channel_metadata_complete(authenticated_client):
    # Real API call to Latent Space channel
    # Verify all metadata fields
    # Assert data types
```

## Test Channel

Integration tests use the **Latent Space** channel (`@LatentSpacePod`) as a test case because:
- It's a public channel with consistent content
- Has a good number of videos for testing
- Represents a real-world use case

## Writing New Tests

### Unit Test Example

```python
def test_new_feature(client, mock_youtube_service):
    # Setup mock
    mock_youtube_service.method.return_value.execute.return_value = {...}
    
    # Call method
    result = client.new_method()
    
    # Assert
    assert result == expected_value
```

### Integration Test Example

```python
@pytest.mark.integration
def test_new_feature_real_api(authenticated_client):
    # Use real API
    result = authenticated_client.new_method()
    
    # Verify with real data
    assert result is not None
    assert "expected_field" in result
```

## Notes

- Integration tests are marked with `@pytest.mark.integration`
- They will be skipped if credentials are not configured
- Unit tests run quickly and don't require API access
- Always run unit tests before committing
- Run integration tests before deploying


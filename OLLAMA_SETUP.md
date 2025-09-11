# Ollama LLM Integration Setup

This document explains how to set up and use the Ollama integration for property description analysis in Immowbot.

## What is Ollama?

Ollama is a tool that allows you to run large language models locally on your machine. Immowbot uses it to analyze property descriptions and provide insights about pros, cons, condition assessment, and value indicators.

## Installation

### 1. Install Ollama

Visit [ollama.ai](https://ollama.ai) and download the installer for your operating system:

- **Windows**: Download the installer and run it
- **macOS**: Download the .app file and drag to Applications
- **Linux**: Run the installation script

### 2. Install a Compatible Model

After installing Ollama, you need to download a language model. We recommend using Llama 3.1 8B for the best balance of performance and quality:

```bash
# Install Llama 3.1 8B (recommended)
ollama pull llama3.1:8b

# Alternative smaller model (faster but less accurate)
ollama pull llama3.1:7b

# Alternative larger model (more accurate but slower)
ollama pull llama3.1:70b
```

### 3. Verify Installation

Check that Ollama is running and your model is available:

```bash
# Check running status
ollama list

# Test the model
ollama run llama3.1:8b "Hello, can you help me analyze real estate?"
```

## Configuration

### Default Settings

Immowbot uses these default settings:
- **Ollama Host**: `http://localhost:11434` (standard Ollama port)
- **Default Model**: `llama3.1:8b`
- **Temperature**: 0.1 (low for consistent analysis)
- **Timeout**: 60 seconds per analysis

### Custom Configuration

You can customize the LLM analyzer by modifying `src/llm_analyzer.py`:

```python
# Use a different model
analyzer = OllamaPropertyAnalyzer(
    ollama_host="http://localhost:11434",
    model_name="llama3.1:70b"  # Use larger model
)
```

## Usage

### Basic Usage

The LLM analysis is enabled by default. Just run Immowbot as usual:

```bash
# Scrape and analyze with LLM
python main.py --max-price 230000 --pages 3

# Analyze existing data with LLM
python main.py --from-json properties_20250110_120000.json
```

### Disable LLM Analysis

If Ollama is not available or you want faster processing:

```bash
python main.py --disable-llm --max-price 230000 --pages 3
```

## Language Support

The LLM analyzer is designed to work with **Dutch property descriptions** (the standard language for Belgian real estate) and provides **all analysis output in English**. The system:

- ✅ **Reads Dutch descriptions** fluently
- ✅ **Translates common terms** (tuin → garden, zolder → attic, etc.)
- ✅ **Outputs everything in English** for international accessibility  
- ✅ **Maintains Belgian context** while explaining in clear English terms

## What the LLM Analysis Provides

The LLM analyzer extracts the following insights from property descriptions:

### 1. Structured Analysis
- **Pros**: Positive aspects and selling points
- **Cons**: Potential concerns or limitations
- **Key Features**: Most important highlights
- **Condition Assessment**: Overall property condition (excellent/good/fair/needs_work)

### 2. Value Indicators
- **Overpriced Signals**: Signs the property might be overpriced
- **Good Value Signals**: Indicators of good value for money
- **Price Justification**: Analysis of price vs features

### 3. Investment Insights
- **Rental Suitability**: How suitable for rental investment
- **Resale Potential**: Likely resale prospects
- **Renovation Opportunity**: Potential for value-adding renovations

### 4. Risk Assessment
- **Red Flags**: Concerning language or omissions
- **Confidence Score**: How confident the AI is in its analysis (0-1)

## Excel Output

The LLM analysis results appear in your Excel export in several places:

### Property Tracking Sheet
New columns added:
- `LLM_CONDITION`: Overall condition assessment
- `LLM_SUMMARY`: Brief summary of the analysis
- `LLM_PROS`: Key positive points
- `LLM_CONS`: Main concerns
- `LLM_CONFIDENCE`: Analysis confidence score

### LLM Analysis Sheet
A dedicated sheet with:
- Overall analysis statistics
- Property condition distribution
- Top-rated properties by confidence
- Common themes across all properties
- Confidence score statistics

## Performance Considerations

### System Requirements
- **RAM**: 8GB minimum, 16GB recommended for 8B models
- **Storage**: 5-10GB for model files
- **CPU**: Modern multi-core processor recommended
- **GPU**: Optional but improves performance significantly

### Processing Time
- **Per Property**: 5-15 seconds depending on model and hardware
- **50 Properties**: ~10-15 minutes with 8B model
- **100 Properties**: ~20-30 minutes with 8B model

### Optimization Tips
1. **Use smaller models** (`o`) for faster analysis
2. **Batch analysis** - process multiple properties in one session
3. **GPU acceleration** - Ollama automatically uses GPU if available
4. **Close other applications** to free up RAM for the model

## Troubleshooting

### Common Issues

#### "Ollama not running"
```bash
# Check if Ollama service is running
ollama list

# If not running, start Ollama
ollama serve
```

#### "Model not found"
```bash
# List available models
ollama list

# Pull the required model
ollama pull llama3.1:8b
```

#### "Connection timeout"
- Check if Ollama is running on port 11434
- Increase timeout in `llm_analyzer.py` if needed
- Ensure no firewall blocking localhost connections

#### "Out of memory"
- Use a smaller model (`llama3.1:7b`)
- Close other memory-intensive applications
- Process fewer properties at once

### Performance Issues

If analysis is too slow:
1. Switch to `llama3.1:7b` model
2. Reduce the number of properties analyzed at once
3. Consider using `--disable-llm` for quick runs

If analysis quality is poor:
1. Upgrade to `llama3.1:70b` model (requires more RAM)
2. Check that property descriptions are in Dutch/English
3. Verify the model is properly loaded

## Advanced Configuration

### Custom Prompts

You can modify the analysis prompt in `src/llm_analyzer.py`, `_create_analysis_prompt()` method to:
- Focus on specific aspects (investment potential, renovation needs)
- Adapt for different property types
- Include local market knowledge

### Integration with Other Models

The system can work with other Ollama models:
- `mistral:7b` - Good alternative to Llama
- `codellama:7b` - If you need technical analysis
- `neural-chat:7b` - Conversational model

### API Configuration

For high-volume usage, consider:
- Running Ollama on a dedicated server
- Using multiple model instances
- Implementing request queuing for batch processing

## Model Recommendations

### For Different Use Cases

| Use Case | Recommended Model | RAM Required | Speed |
|----------|------------------|--------------|-------|
| Quick analysis | `llama3.1:7b` | 8GB | Fast |
| Balanced | `llama3.1:8b` | 12GB | Medium |
| High accuracy | `llama3.1:70b` | 48GB+ | Slow |
| Development/Testing | `llama3.1:7b` | 8GB | Fast |

### Model Performance Comparison

Based on property analysis quality:
1. **llama3.1:70b** - Most accurate, best insights
2. **llama3.1:8b** - Good balance of speed and quality
3. **llama3.1:7b** - Fastest, adequate for basic analysis
4. **mistral:7b** - Good alternative, different analysis style

## Support

If you encounter issues:
1. Check Ollama documentation at [ollama.ai/docs](https://ollama.ai/docs)
2. Verify system requirements are met
3. Test with a smaller dataset first
4. Consider using `--disable-llm` as a fallback
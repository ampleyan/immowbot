# Immowbot Troubleshooting Guide

## Common Issues and Solutions

### 1. Chrome WebDriver Issues

**Problem**: `[WinError 193] %1 is not a valid Win32 application`

**Solutions**:
- **Clear WebDriver cache**: Delete folder `C:\Users\[username]\.wdm`
- **Install Chrome browser**: Make sure Google Chrome is installed and updated
- **Run as administrator**: Try running the command prompt as administrator
- **Use manual input**: If WebDriver continues to fail, use `python manual_data_input.py`

### 2. HTTP 403 Forbidden Errors

**Problem**: Website returns "HTTP 403" - blocking automated requests

**Solutions**:
- **Use VPN**: Connect to a VPN to change your IP address
- **Browser first**: Visit immoweb.be manually in your browser before running the script
- **Reduce frequency**: Use fewer pages (`--pages 1` or `--pages 2`)
- **Manual entry**: Use `python manual_data_input.py` to enter data manually

### 3. No Properties Found

**Problem**: Script runs but finds 0 properties

**Possible causes**:
- Filters too restrictive (very low max-price, very high min-surface)
- Postal codes don't have properties matching criteria
- Website structure changes

**Solutions**:
- **Broaden filters**: Increase max-price, decrease min-surface
- **Test different areas**: Try different postal codes
- **Remove EPC filter**: Remove `--epc-scores` to see more properties
- **Manual verification**: Check immoweb.be manually with same criteria

### 4. Dependencies Issues

**Problem**: Import errors or missing packages

**Solutions**:
```bash
# Reinstall dependencies
pip uninstall -y selenium webdriver-manager
pip install -r requirements.txt

# If still issues, install individually:
pip install selenium==4.15.2
pip install webdriver-manager==4.0.1
pip install beautifulsoup4==4.12.2
pip install pandas==2.1.3
```

## Alternative Approaches

### Manual Data Entry

If automated scraping fails completely:

1. Run `python manual_data_input.py`
2. Visit immoweb.be manually
3. Search with your criteria
4. Copy data from each property into the tool
5. Generate analysis from manual data

### Browser-Based Approach

1. Open immoweb.be in your browser
2. Apply your search filters
3. Copy property URLs
4. Use a browser extension or manually collect data
5. Use the manual input tool

### Reduced Automation

```bash
# Try with minimal filters first
python main.py --max-price 300000 --pages 1

# If that works, gradually add filters
python main.py --max-price 250000 --min-surface 50 --pages 1
```

## Getting Help

### Check Log Output

The tool provides detailed logging. Look for:
- Chrome driver installation path
- HTTP response codes
- Specific error messages

### Test Commands

```bash
# Test basic functionality
python test_scraper.py

# Test with your criteria but limited scope
python main.py --max-price 230000 --pages 1

# Use the ready-made test script
python run_analysis.py
```

### Report Issues

If you encounter persistent issues:

1. Note your exact command
2. Save the full error output
3. Check your Chrome browser version
4. Try manual data entry as workaround

## Tips for Success

1. **Start small**: Test with `--pages 1` first
2. **Be patient**: Add delays between requests
3. **Use realistic filters**: Don't make criteria too restrictive
4. **Have backup plan**: Manual data entry works when automation fails
5. **Respect the website**: Don't run multiple instances simultaneously

## System Requirements

- **Chrome Browser**: Must be installed and updated
- **Python 3.12**: Check with `python --version`
- **Internet connection**: Stable connection required
- **Disk space**: At least 100MB for WebDriver cache
import pytest
import re
from src.config import load_config

# Exact regex pattern used in C# ChatController.cs ContainsScriptingSymbols
CS_SECURITY_PATTERN = r"<|>|script|alert|onclick|onload|onerror|document|eval"
security_regex = re.compile(CS_SECURITY_PATTERN, re.IGNORECASE)

def contains_scripting_symbols(text: str) -> bool:
    return bool(security_regex.search(text))

def test_csharp_security_filter_regex():
    # Positive tests: things that SHOULD be flagged
    assert contains_scripting_symbols("<script>")
    assert contains_scripting_symbols("alert('hello')")
    assert contains_scripting_symbols("onclick=doSomething()")
    assert contains_scripting_symbols("document.write()")
    assert contains_scripting_symbols("eval('1+1')")
    assert contains_scripting_symbols("<")
    assert contains_scripting_symbols(">")
    assert contains_scripting_symbols("SCRIPT tag is bad")
    assert contains_scripting_symbols("DocuMent.getElementById")
    
    # Negative tests: things that SHOULD NOT be flagged
    assert not contains_scripting_symbols("Hello, how can I help you today?")
    assert not contains_scripting_symbols("UPSDM helpline number is 0522-4944200.")
    assert not contains_scripting_symbols("Please visit the official website upsdm.gov.in.")
    assert not contains_scripting_symbols("You can download the candidate application form here.")
    assert not contains_scripting_symbols("This file contains circulars.")

def test_greeting_responses_are_compliant():
    config = load_config()
    greetings = config.greeting_responses
    
    for lang, responses in greetings.items():
        if isinstance(responses, list):
            for response in responses:
                assert not contains_scripting_symbols(response), f"Greeting response for '{lang}' contains scripting symbols: {response}"
        else:
            assert not contains_scripting_symbols(responses), f"Greeting response for '{lang}' contains scripting symbols: {responses}"

def test_fallback_responses_are_compliant():
    config = load_config()
    fallbacks = config.fallback_responses
    
    for lang, response in fallbacks.items():
        assert not contains_scripting_symbols(response), f"Fallback response for '{lang}' contains scripting symbols!"

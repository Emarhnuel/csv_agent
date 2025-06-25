import sys
from contextlib import contextmanager
from io import StringIO
import re

class StreamlitProcessOutput:
    """Class to handle capturing and displaying process output in Streamlit."""
    
    def __init__(self, container):
        self.container = container
        self.output_text = ""
        self.seen_lines = set()
        self.seen_patterns = set()
        
        # Track key milestones to prevent duplicate update messages
        self.milestone_seen = {
            "search": False,
            "extract": False,
            "process": False,
            "generate": False,
            "complete": False
        }
        
    def clean_text(self, text):
        """Clean ANSI codes and formatting from text."""
        # Remove ANSI escape codes
        ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
        text = ansi_escape.sub('', text)
        
        # Clean up other formatting
        text = text.replace('[1m', '').replace('[95m', '').replace('[92m', '').replace('[00m', '')
        return text
    
    def extract_core_message(self, line):
        """Extract the meaningful core of a message, removing variable parts."""
        # Remove UUIDs, timestamps, and other noise
        line = re.sub(r'[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}', '', line)
        line = re.sub(r'\d{1,2}/\d{1,2}/\d{4}', 'DATE', line)
        line = re.sub(r'\d+\.\d+', 'NUMBER', line)
        line = re.sub(r'c:\\\\users\\\\.*?\\\\', 'PATH/', line)  # Double escapes for backslashes
        
        # Remove line metadata parts
        metadata_prefixes = ["🚀 Crew:", "│", "├", "└", "--", "##"]
        for prefix in metadata_prefixes:
            if line.startswith(prefix):
                parts = line.split(' ', 2)
                if len(parts) > 2:
                    line = parts[2]  # Keep only the message part
        
        return line.lower().strip()
    
    def is_duplicate_content(self, line):
        """Check if this line contains duplicate information we've already shown."""
        # Get the core message
        core_message = self.extract_core_message(line)
        
        # Skip very short messages as they're likely not informative
        if len(core_message) < 5:
            return True
            
        # Check if we've seen this core message before
        if core_message in self.seen_patterns:
            return True
            
        # Store the core message
        self.seen_patterns.add(core_message)
        return False
        
    def write(self, text):
        """Write text to the Streamlit container."""
        cleaned_text = self.clean_text(text)
        if not cleaned_text:
            return
            
        # Split into lines and process each line
        lines = cleaned_text.split('\n')
        new_lines = []
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # Skip if we've seen the exact line before
            if line in self.seen_lines:
                continue
                
            # Skip if we've seen similar content before
            if self.is_duplicate_content(line):
                continue
                
            # Check if this is a useful line to display
            if self.is_useful_line(line):
                self.seen_lines.add(line)
                new_lines.append(line)
        
        if new_lines:
            # Add the new lines to the output
            new_content = '\n'.join(new_lines)
            self.output_text = f"{self.output_text}\n{new_content}" if self.output_text else new_content
            
            # Update the display
            self.container.text(self.output_text)
    
    def is_useful_line(self, line):
        """Determine if this line contains useful information for the user."""
        line_lower = line.lower()
        
        # Always keep emoji milestone markers
        if any(emoji in line for emoji in ["🔍", "✅", "⏳", "🚀"]):
            # Track milestone type to prevent duplicates
            if "processing" in line_lower:
                if self.milestone_seen["process"]:
                    return False
                self.milestone_seen["process"] = True
            elif "complete" in line_lower:
                if self.milestone_seen["complete"]:
                    return False
                self.milestone_seen["complete"] = True
                
            return True
            
        # Always keep error messages
        if "error" in line_lower or "failed" in line_lower or "warning" in line_lower:
            return True
            
        # Keep successful PDF operations
        if "successfully filled pdf" in line_lower:
            return True
        
        # Keep patient search information
        if "searching for patient" in line_lower:
            if self.milestone_seen["search"]:
                return False
            self.milestone_seen["search"] = True
            return True
            
        # Filter out all the noise
        if any(noise in line_lower for noise in [
            "crew execution",
            "task", 
            "id:", 
            "status:",
            "using",
            "tool usage",
            "reasoning",
            "understanding",
            "1.",
            "agent:",
            "-",
            "retrieve",
            "{",
            "}",
            "|",
            "├",
            "└"
        ]):
            return False
            
        # If we get here, only keep important action words
        return any(action in line_lower for action in [
            "extract",
            "generat",
            "process",
            "search",
            "map",
            "complet",
            "fill",
            "saved"
        ])
        
    def flush(self):
        """Implement flush method required for stream compatibility."""
        pass

@contextmanager
def capture_output(container):
    """Capture stdout and redirect it to a Streamlit container."""
    string_io = StringIO()
    output_handler = StreamlitProcessOutput(container)
    old_stdout = sys.stdout
    sys.stdout = output_handler
    try:
        yield string_io
    finally:
        sys.stdout = old_stdout

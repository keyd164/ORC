"""Local, read-only business analysis workflow."""
import os

# Keep prompts, tool inputs and bill results out of hosted tracing services.
os.environ['LANGSMITH_TRACING'] = 'false'
os.environ['LANGCHAIN_TRACING_V2'] = 'false'

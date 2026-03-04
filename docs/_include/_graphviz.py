import graphviz
import contextlib, io
from IPython.display import display
from IPython.display import SVG
from IPython.display import HTML

def _extract_inner_dot(code):
    """Extract content inside the first '{' and last '}' if the code starts with 'digraph'."""
    code = code.strip()
    if code.startswith('digraph'):
        start = code.find('{')
        end = code.rfind('}')
        if start != -1 and end != -1 and end > start:
            return code[start+1:end].strip()
    return code

def _clean_dot_text(text):
    if not text:
        return ""
    
    import unicodedata
    text = unicodedata.normalize('NFC', text)
    
    clean_bytes = text.encode('utf-8', errors='ignore')
    text = clean_bytes.decode('utf-8')
    return text

def dot(code):
    src = graphviz.Source(_clean_dot_text(code))    
    src.format = 'pdf'   # or 'svg' depending on your needs
    with contextlib.redirect_stderr(io.StringIO()):
        return display(src)

def dot_svg(code, h="150px"):
    inner = _extract_inner_dot(code)
    src = graphviz.Source(f"digraph G {{ graph [ratio=shrink]; {inner} }}")
    
    svg_str = src.pipe(format='svg').decode('utf-8')
    styled_svg = svg_str.replace('<svg ', f'<svg style="height:{h}; width:auto;" ')
    
    return display(HTML(styled_svg))
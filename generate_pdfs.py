#!/usr/bin/env python3
"""
Generate PDF files from Markdown documents
"""

import markdown2
from weasyprint import HTML, CSS
import os

def markdown_to_pdf(markdown_file, pdf_file):
    """Convert markdown file to PDF with styling"""

    # Read markdown content
    with open(markdown_file, 'r', encoding='utf-8') as f:
        markdown_content = f.read()

    # Convert markdown to HTML with extras for better formatting
    html_content = markdown2.markdown(
        markdown_content,
        extras=[
            'fenced-code-blocks',
            'tables',
            'break-on-newline',
            'code-friendly',
            'cuddled-lists',
            'header-ids'
        ]
    )

    # Create full HTML document with styling
    full_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');

            body {{
                font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                line-height: 1.6;
                color: #333;
                max-width: 900px;
                margin: 0 auto;
                padding: 40px 20px;
                background: white;
            }}

            h1 {{
                color: #0C62FB;
                border-bottom: 3px solid #0C62FB;
                padding-bottom: 10px;
                margin-top: 40px;
                font-size: 2.5em;
            }}

            h2 {{
                color: #0C62FB;
                margin-top: 30px;
                font-size: 1.8em;
                border-bottom: 1px solid #e0e0e0;
                padding-bottom: 8px;
            }}

            h3 {{
                color: #333;
                margin-top: 25px;
                font-size: 1.3em;
                font-weight: 600;
            }}

            h4 {{
                color: #666;
                margin-top: 20px;
                font-size: 1.1em;
                font-weight: 600;
            }}

            pre {{
                background-color: #f6f8fa;
                padding: 15px;
                border-radius: 6px;
                overflow-x: auto;
                font-family: 'Courier New', Courier, monospace;
                font-size: 0.9em;
                line-height: 1.4;
                border: 1px solid #d1d5da;
                page-break-inside: avoid;
            }}

            code {{
                background-color: #f3f4f6;
                padding: 2px 6px;
                border-radius: 3px;
                font-family: 'Courier New', Courier, monospace;
                font-size: 0.9em;
            }}

            pre code {{
                background-color: transparent;
                padding: 0;
            }}

            ul, ol {{
                margin: 15px 0;
                padding-left: 30px;
            }}

            li {{
                margin: 8px 0;
            }}

            strong {{
                color: #000;
                font-weight: 600;
            }}

            em {{
                color: #555;
            }}

            blockquote {{
                border-left: 4px solid #0C62FB;
                padding-left: 20px;
                margin: 20px 0;
                color: #666;
                background: #f9f9f9;
                padding: 15px 20px;
            }}

            table {{
                border-collapse: collapse;
                width: 100%;
                margin: 20px 0;
            }}

            th, td {{
                border: 1px solid #ddd;
                padding: 12px;
                text-align: left;
            }}

            th {{
                background-color: #0C62FB;
                color: white;
                font-weight: 600;
            }}

            tr:nth-child(even) {{
                background-color: #f9f9f9;
            }}

            /* Special styling for diagram/ASCII art */
            pre:has(> code:not([class])) {{
                background: #f8f9fa;
                border: 2px solid #0C62FB;
                padding: 20px;
                font-size: 0.8em;
                line-height: 1.2;
            }}

            /* Page break controls */
            h1, h2 {{
                page-break-after: avoid;
            }}

            pre, table, blockquote {{
                page-break-inside: avoid;
            }}

            /* Emoji support */
            .emoji {{
                font-size: 1.2em;
                vertical-align: middle;
            }}

            /* Link styling */
            a {{
                color: #0C62FB;
                text-decoration: none;
            }}

            a:hover {{
                text-decoration: underline;
            }}

            /* Print-specific styles */
            @media print {{
                body {{
                    padding: 20px;
                    font-size: 11pt;
                }}

                h1 {{
                    font-size: 24pt;
                }}

                h2 {{
                    font-size: 18pt;
                }}

                pre {{
                    font-size: 9pt;
                }}
            }}
        </style>
    </head>
    <body>
        {html_content}
    </body>
    </html>
    """

    # Generate PDF using WeasyPrint
    HTML(string=full_html).write_pdf(pdf_file)
    print(f"✅ Generated PDF: {pdf_file}")

def main():
    """Generate PDFs for both documents"""

    # Define file paths
    docs = [
        ('CONCEPTUAL_OVERVIEW.md', 'PBI_Consolidation_Tool_Conceptual_Overview.pdf'),
        ('EXECUTIVE_SUMMARY.md', 'PBI_Consolidation_Tool_Executive_Summary.pdf')
    ]

    # Generate PDFs
    for md_file, pdf_file in docs:
        if os.path.exists(md_file):
            try:
                markdown_to_pdf(md_file, pdf_file)
            except Exception as e:
                print(f"❌ Error generating {pdf_file}: {str(e)}")
                print("Trying alternative method with pdfkit...")

                # Alternative method using pdfkit (requires wkhtmltopdf)
                try:
                    import pdfkit
                    pdfkit.from_file(md_file, pdf_file)
                    print(f"✅ Generated PDF using pdfkit: {pdf_file}")
                except Exception as e2:
                    print(f"❌ Alternative method also failed: {str(e2)}")
        else:
            print(f"❌ File not found: {md_file}")

    print("\n📄 PDF generation complete!")

if __name__ == "__main__":
    main()
#!/usr/bin/env python3
"""
Generate PDF files from Markdown documents using a simple approach
"""

import os
import sys

def install_required_packages():
    """Install required packages if not present"""
    try:
        import markdown
        import pdfkit
    except ImportError:
        print("Installing required packages...")
        os.system(f"{sys.executable} -m pip install markdown pdfkit")

def markdown_to_pdf_simple(markdown_file, pdf_file):
    """Convert markdown to PDF using pdfkit"""
    import markdown
    import pdfkit

    # Read markdown content
    with open(markdown_file, 'r', encoding='utf-8') as f:
        markdown_content = f.read()

    # Convert markdown to HTML
    html_content = markdown.markdown(
        markdown_content,
        extensions=['extra', 'codehilite', 'toc', 'tables', 'fenced_code']
    )

    # Create full HTML with professional styling
    full_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            body {{
                font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
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
                font-size: 32px;
                page-break-before: auto;
            }}

            h1:first-child {{
                margin-top: 0;
            }}

            h2 {{
                color: #0C62FB;
                margin-top: 30px;
                font-size: 24px;
                border-bottom: 1px solid #e0e0e0;
                padding-bottom: 8px;
                page-break-after: avoid;
            }}

            h3 {{
                color: #333;
                margin-top: 25px;
                font-size: 18px;
                font-weight: 600;
            }}

            h4 {{
                color: #666;
                margin-top: 20px;
                font-size: 16px;
                font-weight: 600;
            }}

            pre {{
                background-color: #f6f8fa;
                padding: 15px;
                border-radius: 6px;
                overflow-x: auto;
                font-family: 'Courier New', monospace;
                font-size: 12px;
                line-height: 1.4;
                border: 1px solid #d1d5da;
                page-break-inside: avoid;
                white-space: pre;
            }}

            code {{
                background-color: #f3f4f6;
                padding: 2px 6px;
                border-radius: 3px;
                font-family: 'Courier New', monospace;
                font-size: 13px;
            }}

            pre code {{
                background-color: transparent;
                padding: 0;
                font-size: 12px;
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
                font-style: italic;
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
                page-break-inside: avoid;
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

            /* Link styling */
            a {{
                color: #0C62FB;
                text-decoration: none;
            }}

            a:hover {{
                text-decoration: underline;
            }}

            /* Special styling for diagrams */
            pre:first-of-type {{
                background: #f8f9fa;
                border: 2px solid #0C62FB;
            }}

            /* Page formatting */
            @page {{
                margin: 2cm;
                size: A4;
            }}

            @media print {{
                body {{
                    padding: 0;
                    font-size: 11pt;
                }}

                h1 {{
                    font-size: 24pt;
                }}

                h2 {{
                    font-size: 18pt;
                }}

                h3 {{
                    font-size: 14pt;
                }}

                pre {{
                    font-size: 9pt;
                    border: 1px solid #ccc;
                }}

                .page-break {{
                    page-break-before: always;
                }}
            }}
        </style>
    </head>
    <body>
        {html_content}
    </body>
    </html>
    """

    # Save HTML temporarily
    temp_html = f"{os.path.splitext(pdf_file)[0]}_temp.html"
    with open(temp_html, 'w', encoding='utf-8') as f:
        f.write(full_html)

    # Configure pdfkit options for better formatting
    options = {
        'page-size': 'A4',
        'margin-top': '20mm',
        'margin-right': '20mm',
        'margin-bottom': '20mm',
        'margin-left': '20mm',
        'encoding': "UTF-8",
        'no-outline': None,
        'enable-local-file-access': None,
        'print-media-type': None
    }

    try:
        # Try to generate PDF using pdfkit
        pdfkit.from_file(temp_html, pdf_file, options=options)
        print(f"✅ Generated PDF: {pdf_file}")

        # Clean up temp HTML file
        os.remove(temp_html)

    except Exception as e:
        print(f"⚠️  pdfkit failed (requires wkhtmltopdf): {str(e)}")
        print(f"📄 HTML file saved at: {temp_html}")
        print("   You can open this HTML file in a browser and print to PDF")

        # Create a helper script for manual conversion
        create_manual_conversion_script(temp_html, pdf_file)

def create_manual_conversion_script(html_file, pdf_file):
    """Create a script that opens the HTML in the default browser"""
    script_content = f"""
#!/bin/bash
echo "Opening HTML file in default browser..."
echo "Please use the browser's Print function to save as PDF"
echo ""
echo "Suggested settings:"
echo "  - Destination: Save as PDF"
echo "  - Layout: Portrait"
echo "  - Paper size: A4 or Letter"
echo "  - Margins: Normal"
echo "  - Options: Background graphics ON"
echo ""
open "{html_file}"
echo ""
echo "Save the PDF as: {pdf_file}"
    """

    script_file = "open_for_pdf_conversion.sh"
    with open(script_file, 'w') as f:
        f.write(script_content)
    os.chmod(script_file, 0o755)
    print(f"📝 Helper script created: {script_file}")

def main():
    """Generate PDFs for both documents"""

    # Install packages if needed
    install_required_packages()

    # Define file paths
    docs = [
        ('CONCEPTUAL_OVERVIEW.md', 'PBI_Consolidation_Tool_Conceptual_Overview.pdf'),
        ('EXECUTIVE_SUMMARY.md', 'PBI_Consolidation_Tool_Executive_Summary.pdf')
    ]

    print("📚 Starting PDF generation...")
    print("-" * 50)

    # Generate PDFs
    for md_file, pdf_file in docs:
        if os.path.exists(md_file):
            print(f"📄 Processing: {md_file}")
            try:
                markdown_to_pdf_simple(md_file, pdf_file)
            except Exception as e:
                print(f"❌ Error: {str(e)}")
        else:
            print(f"❌ File not found: {md_file}")
        print("-" * 50)

    print("\n✨ PDF generation complete!")
    print("\nNote: If PDFs were not generated automatically, you can:")
    print("1. Open the generated HTML files in your browser")
    print("2. Use the browser's Print > Save as PDF function")
    print("3. Or install wkhtmltopdf: brew install --cask wkhtmltopdf")

if __name__ == "__main__":
    main()
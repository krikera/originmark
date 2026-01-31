import json
from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.syntax import Syntax

from .core import OriginMark

console = Console()


@click.group()
@click.option('--api-url', envvar='ORIGINMARK_API_URL', help='API URL for remote operations')
@click.pass_context
def main(ctx, api_url):
    """OriginMark CLI - Digital signature verification for AI content"""
    ctx.obj = OriginMark(api_url=api_url)


@main.command()
@click.argument('file', type=click.Path(exists=True, path_type=Path))
@click.option('--author', help='Author name')
@click.option('--model', help='AI model used')
@click.option('--private-key', help='Base64 encoded private key')
@click.option('--use-api', is_flag=True, help='Use API instead of local signing')
@click.option('--format', type=click.Choice(['json', 'c2pa']), default='json', help='Output format (json or c2pa)')
@click.pass_obj
def sign(obj: OriginMark, file: Path, author: Optional[str], model: Optional[str], 
         private_key: Optional[str], use_api: bool, format: str):
    """Sign a file and create signature metadata"""
    console.print(f"[bold blue]Signing file:[/bold blue] {file}")
    
    metadata = {}
    if author:
        metadata['author'] = author
    if model:
        metadata['model_used'] = model
    if format == 'c2pa':
        metadata['format'] = 'c2pa'
    
    try:
        if use_api:
            if not obj.api_url:
                console.print("[bold red]Error:[/bold red] API URL not configured")
                return
            result = obj.sign_with_api(file, metadata)
        else:
            result = obj.sign_file(file, metadata, private_key)
        
        # Display result
        table = Table(title="Signature Details", show_header=True)
        table.add_column("Field", style="cyan")
        table.add_column("Value", style="green")
        
        table.add_row("ID", result['id'])
        table.add_row("Content Hash", result['content_hash'][:32] + "...")
        table.add_row("Public Key", result['public_key'][:32] + "...")
        table.add_row("Timestamp", result['timestamp'])
        
        # Show format if C2PA
        if format == 'c2pa':
            table.add_row("Format", "C2PA (Content Authenticity Initiative)")
            if 'manifest' in result:
                table.add_row("C2PA Manifest", "✓ Generated")
        
        if 'private_key' in result:
            table.add_row("Private Key", result['private_key'][:32] + "...")
            console.print("\n[bold yellow]  Save the private key securely![/bold yellow]")
        
        console.print(table)
        
        # Save location
        if not use_api:
            sidecar_path = file.with_suffix(file.suffix + ".originmark.json")
            console.print(f"\n[bold green]✓[/bold green] Signature saved to: {sidecar_path}")
        
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {str(e)}")


@main.command()
@click.argument('file', type=click.Path(exists=True, path_type=Path))
@click.option('--sidecar', type=click.Path(exists=True, path_type=Path), help='Path to sidecar JSON')
@click.option('--signature-id', help='Signature ID for API verification')
@click.option('--use-api', is_flag=True, help='Use API for verification')
@click.pass_obj
def verify(obj: OriginMark, file: Path, sidecar: Optional[Path], 
           signature_id: Optional[str], use_api: bool):
    """Verify a file signature"""
    console.print(f"[bold blue]Verifying file:[/bold blue] {file}")
    
    try:
        if use_api:
            if not obj.api_url:
                console.print("[bold red]Error:[/bold red] API URL not configured")
                return
            result = obj.verify_with_api(file, signature_id=signature_id)
        else:
            result = obj.verify_file(file, sidecar)
        
        # Display result
        if result['valid']:
            console.print("\n[bold green]✓ Signature Verified Successfully![/bold green]")
            
            if 'metadata' in result and result['metadata']:
                metadata = result['metadata']
                table = Table(title="Content Metadata", show_header=True)
                table.add_column("Field", style="cyan")
                table.add_column("Value", style="green")
                
                for key, value in metadata.items():
                    table.add_row(key.replace('_', ' ').title(), str(value))
                
                console.print(table)
        else:
            console.print(f"\n[bold red]✗ Verification Failed:[/bold red] {result['message']}")
        
        if result.get('content_hash'):
            console.print(f"\n[dim]Content Hash: {result['content_hash']}[/dim]")
            
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {str(e)}")


@main.command()
def generate_keys():
    """Generate a new Ed25519 keypair"""
    console.print("[bold blue]Generating new keypair...[/bold blue]")
    
    om = OriginMark()
    signing_key, verify_key = om.generate_keypair()
    
    import nacl.encoding
    private_key = nacl.encoding.Base64Encoder.encode(bytes(signing_key)).decode()
    public_key = nacl.encoding.Base64Encoder.encode(bytes(verify_key)).decode()
    
    table = Table(title="Generated Keypair", show_header=True)
    table.add_column("Key Type", style="cyan")
    table.add_column("Value", style="green")
    
    table.add_row("Private Key", private_key)
    table.add_row("Public Key", public_key)
    
    console.print(table)
    console.print("\n[bold yellow]  Keep your private key secure and never share it![/bold yellow]")


@main.command()
@click.argument('signature_id', help='Signature ID to export')
@click.option('--output', type=click.Path(path_type=Path), help='Output file for C2PA manifest')
@click.pass_obj
def export_c2pa(obj: OriginMark, signature_id: str, output: Optional[Path]):
    """Export a signature in C2PA format"""
    console.print(f"[bold blue]Exporting signature to C2PA format:[/bold blue] {signature_id}")
    
    try:
        if not obj.api_url:
            console.print("[bold red]Error:[/bold red] API URL not configured. C2PA export requires API access.")
            return
            
        import requests
        response = requests.get(f"{obj.api_url}/signatures/{signature_id}/c2pa")
        response.raise_for_status()
        
        c2pa_data = response.json()
        
        # Display C2PA info
        table = Table(title="C2PA Export", show_header=True)
        table.add_column("Field", style="cyan")
        table.add_column("Value", style="green")
        
        table.add_row("Signature ID", c2pa_data['signature_id'])
        table.add_row("Content Hash", c2pa_data['content_hash'][:32] + "...")
        table.add_row("Signed At", c2pa_data['signed_at'])
        table.add_row("Format", "C2PA (Content Authenticity Initiative)")
        
        console.print(table)
        
        # Save to file if specified
        if output:
            output.write_text(json.dumps(c2pa_data, indent=2))
            console.print(f"\n[bold green]✓[/bold green] C2PA manifest saved to: {output}")
        else:
            # Pretty print manifest
            json_str = json.dumps(c2pa_data['c2pa_manifest'], indent=2)
            syntax = Syntax(json_str, "json", theme="monokai", line_numbers=True)
            panel = Panel(syntax, title="C2PA Manifest", border_style="green")
            console.print("\n", panel)
        
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {str(e)}")


@main.command()
@click.argument('sidecar', type=click.Path(exists=True, path_type=Path))
def show_signature(sidecar: Path):
    """Display signature details from a sidecar JSON file"""
    try:
        data = json.loads(sidecar.read_text())
        
        # Pretty print JSON
        json_str = json.dumps(data, indent=2)
        syntax = Syntax(json_str, "json", theme="monokai", line_numbers=True)
        
        panel = Panel(syntax, title=f"Signature: {sidecar.name}", border_style="blue")
        console.print(panel)
        
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {str(e)}")


if __name__ == '__main__':
    main() 
"""
Command-line interface for PII/PCI Data Redaction Gateway.
"""
import click
import json
import asyncio
from rich.console import Console
from rich.table import Table
from rich.syntax import Syntax
from rich import print as rprint
import httpx

from ..config import get_config

console = Console()


@click.group()
def cli():
    """PII/PCI Data Redaction Gateway CLI"""
    pass


@cli.command()
@click.option('--host', default=None, help='Host to bind to')
@click.option('--port', default=None, help='Port to bind to')
@click.option('--reload', is_flag=True, help='Enable auto-reload')
def serve(host, port, reload):
    """Start the redaction gateway server."""
    import uvicorn
    from ..api import app
    
    # Load configuration
    config = get_config()
    
    # Use config defaults if not provided
    host = host or config.server.host
    port = port or config.server.port
    
    console.print(f"[green]Starting {config.name} v{config.version}...[/green]")
    console.print(f"[blue]Server: http://{host}:{port}[/blue]")
    console.print(f"[yellow]Environment: {config.environment}[/yellow]")
    
    uvicorn.run(
        app,
        host=host,
        port=port,
        reload=reload,
        workers=1 if reload else config.server.workers
    )


@cli.command()
@click.argument('input_file', type=click.File('r'))
@click.option('--api-key', default=None, help='API key')
@click.option('--url', default=None, help='API URL')
def redact(input_file, api_key, url):
    """Redact data from a JSON file."""
    config = get_config()
    
    # Use config defaults if not provided
    api_key = api_key or (config.security.api_keys[0] if config.security.api_keys else 'dev-api-key-12345')
    url = url or f"http://{config.server.host}:{config.server.port}"
    
    async def _redact():
        # Load input data
        data = json.load(input_file)
        
        # Prepare request
        payload = {
            "data": data,
            "include_meta": True
        }
        
        headers = {
            "X-API-Key": api_key,
            "Content-Type": "application/json"
        }
        
        # Send request
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    f"{url}/redact",
                    json=payload,
                    headers=headers,
                    timeout=30.0
                )
                response.raise_for_status()
                result = response.json()
                
                # Display result
                console.print("\n[green]✓ Redaction Complete[/green]\n")
                
                # Show redacted data
                console.print("[bold]Redacted Data:[/bold]")
                syntax = Syntax(
                    json.dumps(result['redacted_data'], indent=2),
                    "json",
                    theme="monokai"
                )
                console.print(syntax)
                
                # Show metadata
                if result.get('redaction_meta'):
                    console.print(f"\n[bold]Redactions: {len(result['redaction_meta'])}[/bold]")
                    
                    table = Table(show_header=True, header_style="bold magenta")
                    table.add_column("Field")
                    table.add_column("Rule")
                    table.add_column("Action")
                    
                    for meta in result['redaction_meta']:
                        table.add_row(
                            meta['field'],
                            meta['rule'],
                            meta['action']
                        )
                    
                    console.print(table)
                
                console.print(f"\n[dim]Processing time: {result['processing_time_ms']:.2f}ms[/dim]")
                
            except httpx.HTTPError as e:
                console.print(f"[red]✗ Error: {e}[/red]")
    
    asyncio.run(_redact())


@cli.command()
@click.argument('input_file', type=click.File('r'))
@click.option('--output', '-o', type=click.File('w'), help='Output file for redacted data')
def dryrun(input_file, output):
    """Perform dry-run showing before/after comparison."""
    from ..engines.base import RedactionEngine
    from ..policy import get_policy_loader
    
    # Load input data
    data = json.load(input_file)
    
    # Get rules and create engine
    policy_loader = get_policy_loader()
    rules = policy_loader.get_rules()
    engine = RedactionEngine(rules)
    
    # Perform redaction
    redacted_data = engine.redact(data)
    meta = engine.get_redaction_meta()
    
    # Display comparison
    console.print("\n[bold yellow]Dry-Run Mode - No data sent to server[/bold yellow]\n")
    
    console.print("[bold]Original Data:[/bold]")
    syntax = Syntax(json.dumps(data, indent=2), "json", theme="monokai")
    console.print(syntax)
    
    console.print("\n[bold]Redacted Data:[/bold]")
    syntax = Syntax(json.dumps(redacted_data, indent=2), "json", theme="monokai")
    console.print(syntax)
    
    # Show metadata
    if meta:
        console.print(f"\n[bold]Redactions: {len(meta)}[/bold]")
        
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Field")
        table.add_column("Rule")
        table.add_column("Action")
        
        for m in meta:
            table.add_row(m.field, m.rule, m.action)
        
        console.print(table)
    
    # Save output if requested
    if output:
        json.dump(redacted_data, output, indent=2)
        console.print(f"\n[green]✓ Redacted data saved to {output.name}[/green]")


@cli.command()
@click.option('--url', default=None, help='API URL')
@click.option('--api-key', default=None, help='API key')
def health(url, api_key):
    """Check service health."""
    config = get_config()
    
    # Use config defaults if not provided
    api_key = api_key or (config.security.api_keys[0] if config.security.api_keys else 'dev-api-key-12345')
    url = url or f"http://{config.server.host}:{config.server.port}"
    
    async def _check_health():
        headers = {"X-API-Key": api_key}
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(f"{url}/health", headers=headers)
                response.raise_for_status()
                result = response.json()
                
                console.print("\n[green]✓ Service is healthy[/green]\n")
                
                table = Table(show_header=False)
                table.add_row("Status", f"[green]{result['status']}[/green]")
                table.add_row("Version", result['version'])
                table.add_row("Policy Version", result.get('policy_version', 'N/A'))
                table.add_row("Uptime", f"{result['uptime_seconds']:.0f}s")
                table.add_row("Cache Size", str(result.get('cache_size', 0)))
                
                console.print(table)
                
            except httpx.HTTPError as e:
                console.print(f"[red]✗ Service unavailable: {e}[/red]")
    
    asyncio.run(_check_health())


@cli.command()
@click.option('--url', default=None, help='API URL')
@click.option('--api-key', default=None, help='API key')
def metrics(url, api_key):
    """Get service metrics."""
    config = get_config()
    
    # Use config defaults if not provided
    api_key = api_key or (config.security.api_keys[0] if config.security.api_keys else 'dev-api-key-12345')
    url = url or f"http://{config.server.host}:{config.server.port}"
    
    async def _get_metrics():
        headers = {config.security.api_key_header_name: api_key}
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(f"{url}/metrics", headers=headers)
                response.raise_for_status()
                result = response.json()
                
                console.print("\n[bold]Service Metrics[/bold]\n")
                
                table = Table(show_header=False)
                table.add_row("Total Requests", str(result['total_requests']))
                table.add_row("Total Redactions", str(result['total_redactions']))
                table.add_row("Avg Latency", f"{result['average_latency_ms']:.2f}ms")
                table.add_row("P95 Latency", f"{result['p95_latency_ms']:.2f}ms")
                table.add_row("P99 Latency", f"{result['p99_latency_ms']:.2f}ms")
                table.add_row("Cache Hit Rate", f"{result['cache_hit_rate']:.2f}%")
                table.add_row("Redaction Coverage", f"{result['redaction_coverage']:.2f}")
                
                console.print(table)
                
            except httpx.HTTPError as e:
                console.print(f"[red]✗ Error: {e}[/red]")
    
    asyncio.run(_get_metrics())


@cli.command()
def validate():
    """Validate policy configuration."""
    from ..policy import get_policy_loader
    from ..policy.validator import PolicyValidator
    
    policy_loader = get_policy_loader()
    policy = policy_loader.get_policy()
    validator = PolicyValidator(policy)
    validation = validator.validate_policy()
    
    if validation['valid']:
        console.print("\n[green]✓ Policy is valid[/green]\n")
    else:
        console.print("\n[red]✗ Policy has errors[/red]\n")
    
    table = Table(show_header=False)
    table.add_row("Total Rules", str(validation['rule_count']))
    table.add_row("Enabled Rules", str(validation['enabled_count']))
    
    console.print(table)
    
    if validation.get('errors'):
        console.print("\n[red bold]Errors:[/red bold]")
        for error in validation['errors']:
            console.print(f"  • {error}")
    
    if validation.get('warnings'):
        console.print("\n[yellow bold]Warnings:[/yellow bold]")
        for warning in validation['warnings']:
            console.print(f"  • {warning}")


if __name__ == '__main__':
    cli()


__all__ = ["cli"]
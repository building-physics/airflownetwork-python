# SPDX-FileCopyrightText: 2023-present Oak Ridge National Laboratory, managed by UT-Battelle
#
# SPDX-License-Identifier: BSD-3-Clause
import click
import json as json_module
import airflownetwork as afn
from typing import TextIO

from ..__about__ import __version__

class ModelContext:
    def __init__(self, model:afn.Model):
        self.model = model
    def audit(self, output:str, json_output:bool=False, indent:int|None=None, no_distribution:bool=False):
        click.echo('Audit operation only supported for epJSON models.')
    def graph(self, output:TextIO, indent:int|None=None, no_distribution:bool=False):
        click.echo('Graph operation only supported for epJSON models.')
    def simulate(self, output:TextIO, steady:bool=True, quiet:bool=False):
        status = None
        if not quiet:
            status=click.echo
        self.model.initialize()
        self.model.airmov(status_function=status)
        afn.write_results_csv([el for el in self.model.nodes.values() if el.index is not None], self.model.links, output)

class EpJsonContext:
    def __init__(self, epjson:dict):
        self.model = epjson
    def audit(self, output, json_output:bool=False, indent:int|None=None, no_distribution:bool=False):
        try:
            auditor = afn.Auditor(self.model, no_distribution=no_distribution)
        except Exception as exc:
            click.echo('Failed to load model to audit: %s' % str(exc))
            return
        # Run the audit
        auditor.audit()
        if json_output:
            if indent:
                json_module.dump(auditor.json, output, indent=indent)
            else:
                json_module.dump(auditor.json, output)
        else:
            output.write('\n'.join(auditor.summarize()))
    def simulation(self, output:TextIO, indent:int|None=None, no_distribution:bool=False):
        click.echo('Simulation operation only supported for JSON models.')
    def graph(self, output:TextIO, no_distribution:bool=False):
        try:
            auditor = afn.Auditor(self.model, no_distribution=no_distribution)
        except Exception as exc:
            click.echo('Failed to load model to graph: %s' % str(exc))
            return
        # Generate the output and write it out
        auditor.write_dot(output)

@click.command()
@click.option('-o', '--output', type=click.Path(writable=True), show_default=True, default='afn.csv',
              help='File name for results output.')
@click.option('-q', '--quiet', is_flag=True, show_default=True, default=False, help='Write out status.')
@click.option('-s', '--steady', is_flag=True, show_default=True, default=True, help='Solve the steady problem.')
@click.pass_context
def simulate(ctx:click.Context, output:TextIO, quiet:bool, steady:bool):
    if not ctx.obj:
        click.echo('Nothing to simulate. Please read in a model first')
        return
    ctx.obj[0].simulate(output, steady=steady, quiet=quiet)

@click.command()
@click.option('-j', '--json', is_flag=True, show_default=True, default=False, help='Write summary in JSON format.')
@click.option('-o', '--output', type=click.File('w'), show_default=True, default='-', help='File name to write.')
@click.option('-i', '--indent', show_default=True, default=0, help='Indent JSON output.')
@click.option('--no-distribution', is_flag=True, show_default=True, default=False, help='Do not evaluate distribution, even if present.')
@click.pass_context
def audit(ctx:click.Context, json:bool, output:TextIO, indent:bool, no_distribution:bool):
    if not ctx.obj:
        click.echo('Nothing to audit. Please read in a model first')
        return
    ctx.obj[0].audit(output, json_output=json, indent=indent, no_distribution=no_distribution)

@click.command()
@click.argument('json', type=click.Path(exists=True))
@click.option('-e', '--epjson', is_flag=True, show_default=True, default=False, help='Read input in the epJSON format.')
@click.pass_context
def read(ctx:click.Context, json:str, epjson:bool):
    ctx.obj.clear()
    if epjson:
        try:
            model = afn.load_epjson(json)
        except Exception as exc:
            click.echo('Failed to open epJSON file "%s": %s' % (json, str(exc)))
            return
        ctx.obj.append(EpJsonContext(model))
    else:
        with open(json, 'r') as fp:
            data = json_module.load(fp)
            model = afn.Model.from_json(data)
        ctx.obj.append(ModelContext(model))

@click.command()
@click.option('-o', '--output', type=click.File('w'), show_default=True, default='graph.dot',
              help='File name to write the dot output.')
@click.option('--no-distribution', is_flag=True, show_default=True, default=False, help='Do not evaluate distribution, even if present.')
@click.pass_context
def graph(ctx:click.Context, output:TextIO, no_distribution:bool):
    if not ctx.obj:
        click.echo('Nothing to audit. Please read in a model first')
        return
    ctx.obj[0].graph(output, no_distribution=no_distribution)

@click.group(context_settings={'help_option_names': ['-h', '--help']}, invoke_without_command=False, chain=True)
@click.version_option(version=__version__, prog_name='airflownetwork')
@click.pass_context
def airflownetwork(ctx:click.Context):
    ctx.obj = [] # We'll use a list for now, later we'll want to be able to load more than one model. But not right now.

airflownetwork.add_command(read)
airflownetwork.add_command(graph)
airflownetwork.add_command(audit)
airflownetwork.add_command(simulate)
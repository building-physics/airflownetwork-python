# SPDX-FileCopyrightText: 2023-present Oak Ridge National Laboratory, managed by UT-Battelle
#
# SPDX-License-Identifier: BSD-3-Clause
import click
import json as json_module
import airflownetwork as afn

from ..__about__ import __version__

@click.command()
@click.argument('epjson', type=click.Path(exists=True))
@click.option('-j', '--json', is_flag=True, show_default=True, default=False, help='Write summary in JSON format.')
#@click.option('-o', '--output', show_default=True, default=None, help='Write output to the specified file.')
@click.option('-o', '--output', type=click.File('w'), show_default=True, default='-', help='File name to write.')
def summarize(epjson, json, output):
    try:
        model = afn.load_epjson(epjson)
    except Exception as exc:
        click.echo('Failed to open epJSON file "%s": %s' % (epjson, str(exc)))
        return
    try:
        auditor = afn.Auditor(model)
    except Exception as exc:
        click.echo('Failed to load model "%s": %s' % (epjson, str(exc)))
        return
    result = auditor.summarize_model(json_output=json)
    output.write('\n'.join(result))

@click.command()
@click.argument('epjson', type=click.Path(exists=True))
@click.option('-o', '--output', type=click.File('w'), show_default=True, default='graph.dot',
              help='File name to write the dot output.')
@click.option('--no-distribution', is_flag=True, show_default=True, default=False, help='Do not evaluate distribution, even if present.')
def graph(epjson, output, no_distribution):
    try:
        model = afn.load_epjson(epjson)
    except Exception as exc:
        click.echo('Failed to open epJSON file "%s": %s' % (epjson, str(exc)))
        return
    try:
        auditor = afn.Auditor(model, no_distribution=no_distribution)
    except Exception as exc:
        click.echo('Failed to load model "%s": %s' % (epjson, str(exc)))
        return
    # Generate the output and write it out
    auditor.write_dot(output)

class ModelContext:
    def __init__(self, model:afn.Model):
        self.model = model
    def audit(self, output, json_output:bool=False, indent:int|None=None, no_distribution:bool=False):
        click.echo('Audit operation only supported for epJSON models.')
    def graph(self, output, indent:int|None=None, no_distribution:bool=False):
        click.echo('Graph operation only supported for epJSON models.')

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
    def graph(self, output, indent:int|None=None, no_distribution:bool=False):
        try:
            auditor = afn.Auditor(self.model, no_distribution=no_distribution)
        except Exception as exc:
            click.echo('Failed to load model to graph: %s' % str(exc))
            return
        # Generate the output and write it out
        auditor.write_dot(output)

@click.command()
@click.option('-j', '--json', is_flag=True, show_default=True, default=False, help='Write summary in JSON format.')
@click.option('-o', '--output', type=click.File('w'), show_default=True, default='-', help='File name to write.')
@click.option('-i', '--indent', show_default=True, default=0, help='Indent JSON output.')
@click.option('--no-distribution', is_flag=True, show_default=True, default=False, help='Do not evaluate distribution, even if present.')
@click.pass_context
def audit(ctx: click.Context, epjson, json, output, indent, no_distribution):
    if ctx.obj is None:
        click.echo('Nothing to audit. Read in a model first')
        return
    ctx.obj.audit(output, json_output=json, indent=indent, no_distribution=no_distribution)

@click.command()
@click.argument('json', type=click.Path(exists=True))
@click.option('-e', '--epjson', is_flag=True, show_default=True, default=False, help='Read input in the epJSON format.')
@click.pass_context
def read(ctx: click.Context, json, epjson):
    if epjson:
        try:
            model = afn.load_epjson(epjson)
        except Exception as exc:
            click.echo('Failed to open epJSON file "%s": %s' % (epjson, str(exc)))
            return
        ctx.obj = EpJsonContext(model)
    else:
        with open(json, 'r') as fp:
            data = json_module.load(fp)
            model = afn.Model.from_json(data)
        ctx.obj = ModelContext(model)

@click.group(context_settings={'help_option_names': ['-h', '--help']}, invoke_without_command=False)
@click.version_option(version=__version__, prog_name='airflownetwork')
@click.pass_context
def airflownetwork(ctx: click.Context):
    ctx.obj = None

airflownetwork.add_command(summarize)
airflownetwork.add_command(graph)
airflownetwork.add_command(audit)
airflownetwork.add_command(read)
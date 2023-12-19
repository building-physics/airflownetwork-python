# SPDX-FileCopyrightText: 2023-present Oak Ridge National Laboratory, managed by UT-Battelle
#
# SPDX-License-Identifier: BSD-3-Clause
import click
import json as json_module
import sys
import airflownetwork as afn

from ..__about__ import __version__

def load_epjson(file):
    with open(file, 'r') as fp:
        model = json_module.load(fp)
    return model

@click.command()
@click.argument('epjson', type=click.Path(exists=True))
@click.option('-j', '--json', is_flag=True, show_default=True, default=False, help='Write summary in JSON format.')
#@click.option('-o', '--output', show_default=True, default=None, help='Write output to the specified file.')
@click.option('-o', '--output', type=click.File('w'), show_default=True, default='-', help='File name to write.')
def summarize(epjson, json, output):
    try:
        model = load_epjson(epjson)
    except Exception as exc:
        click.echo('Failed to open epJSON file "%s": %s' % (epjson, str(exc)))
        return
    auditor = afn.Auditor(model)
    result = auditor.summarize_model(json_output=json)
    output.write('\n'.join(result))

@click.command()
@click.argument('epjson', type=click.Path(exists=True))
@click.option('-o', '--output', type=click.File('w'), show_default=True, default='graph.dot',
              help='File name to write the dot output.')
def graph(epjson, output):
    try:
        model = load_epjson(epjson)
    except Exception as exc:
        click.echo('Failed to open epJSON file "%s": %s' % (epjson, str(exc)))
        return
    auditor = afn.Auditor(model)
    # Generate the output and write it out
    auditor.write_dot(output)

@click.command()
@click.argument('epjson', type=click.Path(exists=True))
@click.option('-j', '--json', is_flag=True, show_default=True, default=False, help='Write summary in JSON format.')
@click.option('-o', '--output', type=click.File('w'), show_default=True, default='-', help='File name to write.')
@click.option('-i', '--indent', show_default=True, default=0, help='Indent JSON output.')
def audit(epjson, json, output, indent):
    try:
        model = load_epjson(epjson)
    except Exception as exc:
        click.echo('Failed to open epJSON file "%s": %s' % (epjson, str(exc)))
        return
    auditor = afn.Auditor(model)
    auditor.audit()

    if json:
        if indent:
            json_module.dump(auditor.json, output, indent=indent)
        else:
            json_module.dump(auditor.json, output)
    else:
        output.write('\n'.join(auditor.summarize()))

@click.group(context_settings={'help_option_names': ['-h', '--help']}, invoke_without_command=False)
@click.version_option(version=__version__, prog_name='airflownetwork')
@click.pass_context
def airflownetwork(ctx: click.Context):
    pass

airflownetwork.add_command(summarize)
airflownetwork.add_command(graph)
airflownetwork.add_command(audit)
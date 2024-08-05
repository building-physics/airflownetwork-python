# SPDX-FileCopyrightText: 2023-present Oak Ridge National Laboratory, managed by UT-Battelle
#
# SPDX-License-Identifier: BSD-3-Clause
import click
import re
import json as json_module
import airflownetwork as afn

from ..__about__ import __version__

@click.command()
@click.argument('epjson', type=click.Path(exists=True))
@click.option('-j', '--json', is_flag=True, show_default=True, default=False, help='Write summary in JSON format.')
#@click.option('-o', '--output', show_default=True, default=None, help='Write output to the specified file.')
@click.option('-o', '--output', type=click.File('w'), show_default=True, default='-', help='File name to write.')
def summarize(epjson, json, output):
    """
    Summarize an EnergyPlus AirflowNetwork model.
    """
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
    """
    Create a graphviz graph of an EnergyPlus AirflowNetwork model.
    """
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

@click.command()
@click.argument('epjson', type=click.Path(exists=True))
@click.option('-j', '--json', is_flag=True, show_default=True, default=False, help='Write summary in JSON format.')
@click.option('-o', '--output', type=click.File('w'), show_default=True, default='-', help='File name to write.')
@click.option('-i', '--indent', show_default=True, default=0, help='Indent JSON output.')
@click.option('--no-distribution', is_flag=True, show_default=True, default=False, help='Do not evaluate distribution, even if present.')
def audit(epjson, json, output, indent, no_distribution):
    """
    Audit an EnergyPlus AirflowNetwork model.
    """
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
    # Run the audit
    auditor.audit()

    if json:
        if indent:
            json_module.dump(auditor.json, output, indent=indent)
        else:
            json_module.dump(auditor.json, output)
    else:
        output.write('\n'.join(auditor.summarize()))

def validate_positive_int(ctx: click.core.Context, param: click.core.Argument, value: str) -> int:
    try:
        v = int(value)
        if v <= 0:
            raise click.BadParameter('Number of elements must be positive.')
        return v
    except ValueError:
        raise click.BadParameter('Number of elements must be an integer.')

@click.command()
@click.argument('epjson', type=click.Path(exists=True))
@click.option('-j', '--json', is_flag=True, show_default=True, default=False, help='Write summary in JSON format.')
@click.option('-o', '--output', type=click.File('w'), show_default=True, default='-', help='File name to write.')
@click.option('-i', '--indent', callback=validate_positive_int, show_default=True, default=0, help='Indent JSON output.')
#@click.option('--no-distribution', is_flag=True, show_default=True, default=False, help='Do not evaluate distribution, even if present.')
@click.option('-v', '--verbose', is_flag=True, show_default=True, default=False, help='Operate verbosely.')
@click.option('-r', '--remove-objects', is_flag=True, show_default=True, default=False, help='Remove incompatible objects.')
@click.option('-s', '--strip', is_flag=True, show_default=True, default=False, help='Strip out extra data added to the model during build process.')
@click.option('--no-openings', is_flag=True, show_default=True, default=False, help='Do not add window or door elements.')
@click.option('--no-windows', is_flag=True, show_default=True, default=False, help='Do not add window elements.')
@click.option('--no-doors', is_flag=True, show_default=True, default=False, help='Do not add door elements.')
@click.option('--windows-may-be-doors', is_flag=True, show_default=True, default=False, help='Doors may be represented as windows in the model.')
@click.option('-w', '--window-filter', type=str, multiple=True, help='Regular expression filter to select windows.')
@click.option('-w', '--door-filter', type=str, multiple=True, help='Regular expression filter to select doors.')
def build(epjson, json, output, indent, verbose, remove_objects, strip, no_openings, no_windows, no_doors, windows_may_be_doors, window_filter, door_filter):
    """
    Add AirflowNetwork inputs to an EnergyPlus model
    """
    try:
        model = afn.load_epjson(epjson)
    except Exception as exc:
        click.echo('Failed to open epJSON file "%s": %s' % (epjson, str(exc)))
        return
    
    window_matchers = []
    for pattern in window_filter:
        window_matchers.append(re.compile(pattern))

    door_matchers = []
    for pattern in door_filter:
        door_matchers.append(re.compile(pattern))

    #try:
    #    auditor = afn.Auditor(model, no_distribution=no_distribution)
    #except Exception as exc:
    #    click.echo('Failed to load model "%s": %s' % (epjson, str(exc)))
    #    return
    # Run the audit
    #auditor.audit()

    #if json:
    #    if indent:
    #        json_module.dump(auditor.json, output, indent=indent)
    #    else:
    #        json_module.dump(auditor.json, output)
    #else:
    #    output.write('\n'.join(auditor.summarize()))

@click.group(context_settings={'help_option_names': ['-h', '--help']}, invoke_without_command=False)
@click.version_option(version=__version__, prog_name='airflownetwork')
@click.pass_context
def airflownetwork(ctx: click.Context):
    pass

airflownetwork.add_command(summarize)
airflownetwork.add_command(graph)
airflownetwork.add_command(audit)
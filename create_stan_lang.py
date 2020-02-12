"""Create create_stan.json."""
import csv
import glob
import json
import re
import sys

# conda install pyyaml
import yaml


def parse_args(argtext):
    """Parse arguments in a function."""
    argtext = re.sub("[()]", "", argtext).strip()
    if argtext == "":
        ret = []
    elif argtext == "~":
        ret = None
    else:
        ret = []
        # , separates args, but they can appear within brackets like int[,]
        for arg in re.split('[|,](?!\\s*])', argtext):
            arg = arg.strip()
            if arg == '...':
                ret.append({'type': '...', 'name': '...'})
            elif arg.startswith('data '):
                # special case for ode solvers
                _data, argtype, argname = arg.split(' ')
                ret.append({'type': "data " + argtype.strip(), 'name': argname.strip()})
            else:
                argtype, argname = arg.split(' ')
                ret.append({'type': argtype.strip(), 'name': argname.strip()})
    return ret


def parse_functions(src, data):
    """
    Parse functions in stan-functions-*.txt.

    stan-functions.txt file is available in the rstan repo.
    rstan/rstan/rstan/tools/stan-functions.txt
    """
    with open(src, "r") as f:
        # Skip commentts
        # https://stackoverflow.com/questions/14158868/python-skip-comment-lines-marked-with-in-csv-dictreader
        reader = csv.reader(filter(lambda row: row[0] != '#', f), delimiter=';')
        # Skip the first non-comment row (StanFunction;Arguments;ReturnType).
        fundata = [row for row in reader][1:]

    functions = {}

    for row in fundata:
        # StanFunction; Arguments; ReturnType
        funname, funargs, funret = row[:3]
        # Ignore sampling statements
        if funargs == "~":
            continue
        else:
            # Ignore target +=
            if re.match(r'target.*\+=$', funname):
                continue
            else:
                try:
                    args = parse_args(funargs)
                except Exception as e:
                    print(
                        "Error parsing arguments in %s" % row, file=sys.stderr)
                    sys.exit(1)
                f = {
                    'return': funret.lstrip(),
                    'args': args,
                }
                if funname in functions:
                    functions[funname]['signatures'].append(f)
                else:
                    vals = {
                        'signatures': [f],
                        'deprecated':
                        False,
                        'lpdf':
                        bool(re.match(r'.*_lpdf$', funname)),
                        'lpmf':
                        bool(re.match(r'.*_lpmf$', funname)),
                        'lcdf':
                        bool(re.match(r'.*_lcdf$', funname)),
                        'lccdf':
                        bool(re.match(r'.*_lccdf$', funname)),
                        'operator':
                        bool(re.match(r'operator', funname)),
                        'keyword':
                        funname in data['keywords']['functions']
                    }
                    vals['density'] = vals['lpdf'] or vals['lpmf']
                    if vals['density']:
                        vals['sampling'] = re.sub(r'_lp[dm]f$', '', funname)
                    else:
                        vals['sampling'] = None
                    vals['math'] = not (vals['lpdf'] or vals['lpmf']
                                        or vals['lcdf'] or vals['lccdf'])
                    functions[funname] = vals
    return functions


def build(file_functions, file_keywords, dst):
    """Build the json file of language definitions."""
    print("functions file: %s" % file_functions)
    with open(file_keywords, 'r') as f:
        data = yaml.load(f, Loader=yaml.FullLoader)
    functions = parse_functions(file_functions, data)
    version = re.search(r"-([0-9]+\.[0-9]+\.[0-9]+)\.txt$",
                        file_functions).group(1)
    print("Stan version: %s" % version)
    data['version'] = version
    data['functions'] = functions
    with open(dst, 'w') as f:
        json.dump(data, f, sort_keys=True, indent=2, separators=(',', ': '))


def main():
    """Command line interface."""
    dst = sys.argv[1]
    file_functions = glob.glob("stan-functions-*.txt")[0]
    print("Using file %s\n" % file_functions)
    file_keywords = 'stan-lang-keywords.yaml'
    build(file_functions, file_keywords, dst)


if __name__ == '__main__':
    main()

"""
Script to convert the data contained in a `.trs` file obtained from a
vector network analyser from RIGOL (e.g. RSA3045N) into a `.csv` file
containing the traces and, optionally, a `.json` file for all the other
settings.
"""
import argparse
import csv
import json
import os


def auto_cast(value: str) -> bool | int | float | str:
    """Cast a string representation of a value into the correct type.

    The string can be a representation of a boolean, an integer or a
    float. If the string can't be cast, it is returned as is.

    Parameters
    ----------
    value : str
        String representation to cast.

    Returns
    -------
    bool | int | float | str
        The value cast in the correct type.
    """
    for caster in (boolify, int, float):
        try:
            return caster(value)
        except ValueError:
            pass
    return value


def boolify(value: str) -> bool:
    """Cast a string into a boolean if it is one, else raises an error.

    Accepted strings are 'True' and 'true' for `True` and 'False' and
    'false' for `False`.

    Parameters
    ----------
    value : str
        String containing the value to cast into a boolean.

    Returns
    -------
    bool
        True if the string is 'True' or 'true' and false if the string
        is 'False' or 'false'.

    Raises
    ------
    ValueError
        If the string is neither 'True', 'true', 'False' or 'false', the
        value can't be converted into a into a boolean.
    """
    if value == 'True' or value == 'true':
        return True
    if value == 'False' or value == 'false':
        return False
    raise ValueError(f"Can't interpret '{value}' as a boolean.")


class File_Type(object):
    """Class to evaluate the validity of a path once called upon.

    Evaluate that a path exists and has the extension specified in the
    constructor.
    """

    def __init__(self, ext: str):
        """Constructor of the class defining the valid extension.

        Parameters
        ----------
        ext : str
            Extension to match to be considered a valid path.

        Raises
        ------
        ValueError
            When the extension doesn't have the for `.***`.
        """
        if not ext.startswith('.'):
            raise ValueError('A file extension begins with a `.`.')
        self.ext = ext

    def __call__(self, path: str) -> str:
        """Validate the existence and the conformity of the given path
        against the defined extension.

        Parameters
        ----------
        path : str
            Path to the file to validate.

        Returns
        -------
        str
            Return the input path if it passes the check.

        Raises
        ------
        TypeError
            If the file doesn't exist or if it doesn't have the right
            extension.
        """
        if not os.path.exists(path):
            raise TypeError(f"File {path} doesn't exist.")

        if os.path.splitext(path)[1] != self.ext:
            raise TypeError(
                f'File {path} as not the right extension ({self.ext})')
        return path


def parse_key(key: str, current_dict: dict, value: any):
    """Split the key in sub dictionaries and assigns the value.

    Creates sub dictionaries of the current dictionary if necessary and
    assigns the value to the last key.

    Parameters
    ----------
    key : str
        Key to parse and split in sub dictionaries.
    current_dict : dict
        Current working dictionary.
    value : any
        Value to assign to the last key.
    """
    # convert all delimitation tokens to be the same (this could be done
    # on the entire content of the file to be faster but I'm not sure if
    # the values could contain these characters)
    key = key.replace('%5B', '\\')
    key = key.replace('%5D.', '\\')
    key = key.replace('%5D', '\\')
    key = key.replace('-%3E', '\\')
    # %20 in url encoding is a space
    key = key.replace('%20', ' ')

    # remove token if it is the last character
    key = key.rstrip('\\')

    # repeatedly process the key as long as there is a delimitation token
    while '\\' in key:
        # split the key at the first token
        sub_dict, key = key.split('\\', 1)
        # create the sub_dict if it doesn't exists
        if sub_dict not in current_dict:
            current_dict[sub_dict] = {}

        # index in the sub dict
        current_dict = current_dict[sub_dict]

    # assign the value
    current_dict[key] = value


def parse_trs(content: str) -> dict:
    """Parse the content of a `.trs` file and insert it in a dictionary.

    Parameters
    ----------
    content : str
        Content of a `.trs` file to parse.

    Returns
    -------
    dict
        Dictionnary representation of the content in the `.trs` file.
    """
    output = {}
    section = ''
    for line in content.splitlines():
        # skip empty line
        if line == '':
            continue

        if line.startswith('[') and line.endswith(']'):
            section = line[1:-1]
            output[section] = {}
            continue

        key, value = line.split('=', 1)

        parse_key(key, output[section], auto_cast(value))

    # FIXME: Some entries may be better in a list but doing so without
    # knowing the following lines raises an issues where a string is
    # used as the index of the list so it would have to be done after
    # going through the file once and require to identify those entries
    # and removing the none integer indexes like 'size' in the 'Trace'
    # subdictionnary.

    return output


def convert(file_path: str, config: bool, trace: bool, memory: bool,
            output: str) -> dict:
    """Convert the content of the specified file with the `parse_trs`
    method, output the desired files and return the converted
    dictionnary.

    Parameters
    ----------
    file_path : str
        Path to the `.trs` file containing the data to be converted.
    config : bool
        Controls the output of a json file containing all the data from
        the file. With an input file `file_name.trs`, the output will be
        `file_name_config.json` in the directory provided by output.
    trace : bool
        Controls the output of a csv file containing the trace from the
        file. With an input file `file_name.trs`, the output will be
        `file_name_trace.csv` in the directory provided by output.
    memory : bool
        Controls the output of a csv file containing the memory trace
        from the file. With an input file `file_name.trs`, the output
        will be `file_name_memory.csv` in the directory provided by
        output.
    output : str
        Directory to save the outputs to.

    Returns
    -------
    dict
        Dictionnary from the `parse_trs` method.
    """

    file_name = os.path.splitext(os.path.basename(file_path))[0]

    with open(file_path, 'r') as file:
        state = parse_trs(file.read())

    if config:
        with open(os.path.join(output, file_name + '_config.json'),
                  'w') as conf_file:
            conf_file.write(json.dumps(state, indent=2))

        step_f = (
            (state['VNAGloble']['m_f64StopFreq']
             - state['VNAGloble']['m_f64StartFreq'])
            / (state['Trace']['size'] - 1))

    if trace:
        with open(os.path.join(output, file_name + '_trace.csv'),
                  'w') as csv_file:
            csv_writer = csv.writer(csv_file, delimiter=',')
            csv_writer.writerow(('frequency', 'real', 'imaginary'))

            csv_writer.writerows([
                (
                    state['VNAGloble']['m_f64StartFreq'] + i * step_f,
                    state['Trace'][f'{i+1}']['ampy'],
                    state['Trace'][f'{i+1}']['ampz'])
                for i in range(state['Trace']['size'])])

    if memory and state['MemoryTrace']['size'] == 0:
        print(f'No memory trace in file {file}, skipping.')
        memory = False

    if memory:
        with open(os.path.join(output, file_name + '_memory.csv'),
                  'w') as csv_file:
            csv_writer = csv.writer(csv_file, delimiter=',')
            csv_writer.writerow(('frequency', 'real', 'imaginary'))

            csv_writer.writerows([
                (
                    state['VNAGloble']['m_f64StartFreq'] + i * step_f,
                    state['MemoryTrace'][f'{i+1}']['ampy'],
                    state['MemoryTrace'][f'{i+1}']['ampz'])
                for i in range(state['MemoryTrace']['size'])])

    return state


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument_group()
    parser.add_argument(
        '-c', '--config',
        action='store_true',
        help='output a json file containing all the data from the `.trs` file '
        'in json format `file_config.json`')
    parser.add_argument(
        '-t', '--trace',
        action='store_true',
        help='output a csv file containing the data from the trace as '
             '`file_trace.csv`')
    parser.add_argument(
        '-m', '--memory',
        action='store_true',
        help='output a csv file containing the data stored in the memory '
             'trace as `file_memory.csv`')
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='increase output verbosity')
    parser.add_argument(
        '-o', '--output-dir',
        help='output directory')
    parser.add_argument(
        'file',
        nargs='+',
        type=File_Type('.trs'),
        help='file to convert')
    args = parser.parse_args()

    if not args.config and not args.trace and not args.memory:
        if args.verbose:
            print('No ouput selected defaulting to `-ct`')
        args.config = True
        args.trace = True

    return args


def main():
    args = parse_args()

    # TODO: Better use of verbosity argument.

    if args.output_dir is not None and not os.path.exists(args.output_dir):
        os.mkdir(args.output_dir)

    for file in args.file:
        if args.verbose:
            print(f'Processing file {file}.')

        if args.output_dir is None:
            convert(file, args.config, args.trace, args.memory,
                    os.path.dirname(file))
        else:
            convert(file, args.config, args.trace, args.memory,
                    args.output_dir)


if __name__ == "__main__":
    main()

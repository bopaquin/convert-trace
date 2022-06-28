"""
Script to convert the data contained in a `.trs` file obtained from a
vector network analyser from RIGOL (e.g. RSA3045N) into a `.csv` file
containing the traces and, optionally, a `.json` file for all the other
data.
"""
import argparse
import csv
import json
import urllib.parse


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

    return output


def parse_key(key: str, current_dict: dict, value: any):

    # convert all delimitation tokens to be the same (this could be done
    # on the entire content of the file to be faster but I'm not sure if
    # the key could contain these characters)
    key = key.replace('%5B', '\\')
    key = key.replace('%5D.', '\\')
    key = key.replace('%5D', '\\')
    key = key.replace('-%3E', '\\')
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

        # index in the new dict
        current_dict = current_dict[sub_dict]

    # assign the value
    current_dict[key] = value


def convert(src_file_name: str):
    with open(src_file_name, 'r') as src_file:
        state = parse_trs(src_file.read())

    with open(src_file_name.replace('trs', 'json'), 'w') as conf_file:
        conf_file.write(json.dumps(state, indent=2))

    with open(src_file_name.replace('trs', 'csv'), 'w') as csv_file:
        csv_writer = csv.writer(csv_file, delimiter=',')
        csv_writer.writerow(('frequency', 'real', 'imaginary'))

        start_f = state['VNAGloble']['m_f64StartFreq']
        stop_f = state['VNAGloble']['m_f64StopFreq']
        size = state['Trace']['size']

        step_f = (stop_f - start_f) / (size - 1)

        csv_writer.writerows([
            (
                start_f + i * step_f,
                state['Trace'][f'{i+1}']['ampy'],
                state['Trace'][f'{i+1}']['ampz'])
            for i in range(size)])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-v', '--verbose', help='increase output verbosity',
                        action='store_true')
    parser.add_argument('file', help='file to convert', type=str)
    args = parser.parse_args()

    convert(args.file)


if __name__ == "__main__":
    main()

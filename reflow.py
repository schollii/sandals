from pprint import pprint
from textwrap import wrap, dedent, fill
import re


def is_list_item(line) -> re.match:
    return line.lstrip().startswith('- ')


def is_blank_line(line) -> bool:
    return line.strip() == ''


def reflow_list_item(group, into_group, width, list_prefix):
    # to dedent list item, need blank + list prefix:
    first_line = group[0]
    indent_len = len(first_line) - len(first_line.lstrip())
    indent = indent_len * ' '
    prefix_len = indent_len + len(list_prefix)

    # dedent, including the list prefix:
    group = [line[prefix_len:] for line in group]

    # rewrap:
    subsequent_indent = indent + ' '*len(list_prefix)
    indent = indent + list_prefix
    blob = '\n'.join(group)
    new_group = wrap(blob, width, initial_indent=indent, subsequent_indent=subsequent_indent) 

    into_group.extend(new_group)


def reflow_paragraph(group, into_group, width):
    first_line = group[0]
    indent_len = len(first_line) - len(first_line.lstrip())
    indent = indent_len * ' '

    blob = dedent('\n'.join(group))
    new_group = wrap(blob, width, initial_indent=indent, subsequent_indent=indent) 

    into_group.extend(new_group)


def reflow(lines: str, width: int=80):
    lines = lines.splitlines()
    reflowed_lines = []
    group = []
    state = 'new'  # state enum
    for line in lines:
        if state == 'new':
            if is_blank_line(line):
                reflowed_lines.append('')
            elif is_list_item(line):
                state = 'list_item'
                group.append(line)
            else:
                state = 'paragraph'
                group.append(line)

        elif state == 'paragraph':
            if is_list_item(line) or is_blank_line(line):
                # end the previous paragraph: time to re-wrap
                if group:
                    reflow_paragraph(group, reflowed_lines, width)
                    group = []

                if is_blank_line(line):
                    reflowed_lines.append('')
                    # print('new paragraph')
                else:
                    state = 'list_item'
                    group.append(line)
                    # print('new list item (after paragraph)')
            
            else:
                group.append(line)

        elif state == 'list_item':
            if is_list_item(line) or is_blank_line(line):
                # new list item or blank marks end of previous item, format it:
                if group:
                    reflow_list_item(group, reflowed_lines, width, '- ')
                    group = []

                if is_blank_line(line):
                    reflowed_lines.append('')
                    state = 'paragraph'
                    # print('new paragraph (after list item)')
                else:
                    # print(f'new list item')
                    group.append(line)

        else:
            raise RuntimeError("BUG! unknown state")

        # pprint(group)

    if state == 'paragraph':
        if group:
            reflow_paragraph(group, reflowed_lines, width)
    elif state == 'list_item':
        if group:
            reflow_list_item(group, reflowed_lines, width, '- ')
    else:
        raise RuntimeError("BUG! unknown state")

    return '\n'.join(reflowed_lines)


lines = '''\
Line 1 asfasdfasdf a sf asdf a sdf as f asdf as f asf aas df asdf as df asdf as f asdfas
Line 2 asfasdfasdf a sf asdf a sdf as f asdf as f asf aas df asdf as df asdf as f asdfas

- item 1 asfasdfasdf a sf asdf a sdf as f asdf as f asf aas df asdf as df asdf as f asdfas
- item 2 asfasdfasdf a sf asdf a sdf as f asdf as f asf aas df asdf as df asdf as f asdfas
    - item 2.1 asfasdfasdf a sf asdf a sdf as f asdf as f asf aas df asdf as df asdf as f asdfas
    - item 2.2 asfasdfasdf a sf asdf a sdf as f asdf as f asf aas df asdf as df asdf as f asdfas
- item 3 asfasdfasdf a sf asdf a sdf as f asdf as f asf aas df asdf as df asdf as f asdfas
- item 4 asfasdfasdf a sf asdf a sdf as f asdf as f asf aas df asdf as df asdf as f asdfas

        Line 1 asfasdfasdf a sf asdf a sdf as f asdf as f asf aas df asdf as df asdf as f asdfas
        Line 2 asfasdfasdf a sf asdf a sdf as f asdf as f asf aas df asdf as df asdf as f asdfas
        - item 1 asfasdfasdf a sf asdf a sdf as f asdf as f asf aas df asdf as df asdf as f asdfas
        - item 2 asfasdfasdf a sf asdf a sdf as f asdf as f asf aas df asdf as df asdf as f asdfas

            - item 2.1 asfasdfasdf a sf asdf a sdf as f asdf as f asf aas df asdf as df asdf as f asdfas
            - item 2.2 asfasdfasdf a sf asdf a sdf as f asdf as f asf aas df asdf as df asdf as f asdfas

    - item 4.1 asfasdfasdf a sf asdf a sdf as f asdf as f asf aas df asdf as df asdf as f asdfas
    - item 4.2 asfasdfasdf a sf asdf a sdf as f asdf as f asf aas df asdf as df asdf as f asdfas

    Line 1 asfasdfasdf a sf asdf a sdf as f asdf as f asf aas df asdf as df asdf as f asdfas
    Line 2 asfasdfasdf a sf asdf a sdf as f asdf as f asf aas df asdf as df asdf as f asdfas

Line 1 asfasdfasdf a sf asdf a sdf as f asdf as f asf aas df asdf as df asdf as f asdfas
Line 2 asfasdfasdf a sf asdf a sdf as f asdf as f asf aas df asdf as df asdf as f asdfas
'''

print(reflow(lines, 40))
print('-------------------------------------------')
print(reflow(lines, 120))



assert reflow(lines, 40) == '''\
Line 1 asfasdfasdf a sf asdf a sdf as f
asdf as f asf aas df asdf as df asdf as
f asdfas Line 2 asfasdfasdf a sf asdf a
sdf as f asdf as f asf aas df asdf as df
asdf as f asdfas

- item 1 asfasdfasdf a sf asdf a sdf as
  f asdf as f asf aas df asdf as df asdf
  as f asdfas
- item 2 asfasdfasdf a sf asdf a sdf as
  f asdf as f asf aas df asdf as df asdf
  as f asdfas
    - item 2.1 asfasdfasdf a sf asdf a
      sdf as f asdf as f asf aas df asdf
      as df asdf as f asdfas
    - item 2.2 asfasdfasdf a sf asdf a
      sdf as f asdf as f asf aas df asdf
      as df asdf as f asdfas
- item 3 asfasdfasdf a sf asdf a sdf as
  f asdf as f asf aas df asdf as df asdf
  as f asdfas
- item 4 asfasdfasdf a sf asdf a sdf as
  f asdf as f asf aas df asdf as df asdf
  as f asdfas

        Line 1 asfasdfasdf a sf asdf a
        sdf as f asdf as f asf aas df
        asdf as df asdf as f asdfas Line
        2 asfasdfasdf a sf asdf a sdf as
        f asdf as f asf aas df asdf as
        df asdf as f asdfas
        - item 1 asfasdfasdf a sf asdf a
          sdf as f asdf as f asf aas df
          asdf as df asdf as f asdfas
        - item 2 asfasdfasdf a sf asdf a
          sdf as f asdf as f asf aas df
          asdf as df asdf as f asdfas

            - item 2.1 asfasdfasdf a sf
              asdf a sdf as f asdf as f
              asf aas df asdf as df asdf
              as f asdfas
            - item 2.2 asfasdfasdf a sf
              asdf a sdf as f asdf as f
              asf aas df asdf as df asdf
              as f asdfas

    - item 4.1 asfasdfasdf a sf asdf a
      sdf as f asdf as f asf aas df asdf
      as df asdf as f asdfas
    - item 4.2 asfasdfasdf a sf asdf a
      sdf as f asdf as f asf aas df asdf
      as df asdf as f asdfas

    Line 1 asfasdfasdf a sf asdf a sdf
    as f asdf as f asf aas df asdf as df
    asdf as f asdfas Line 2 asfasdfasdf
    a sf asdf a sdf as f asdf as f asf
    aas df asdf as df asdf as f asdfas

Line 1 asfasdfasdf a sf asdf a sdf as f
asdf as f asf aas df asdf as df asdf as
f asdfas Line 2 asfasdfasdf a sf asdf a
sdf as f asdf as f asf aas df asdf as df
asdf as f asdfas'''

assert reflow(lines, 120) == '''\
Line 1 asfasdfasdf a sf asdf a sdf as f asdf as f asf aas df asdf as df asdf as f asdfas Line 2 asfasdfasdf a sf asdf a
sdf as f asdf as f asf aas df asdf as df asdf as f asdfas

- item 1 asfasdfasdf a sf asdf a sdf as f asdf as f asf aas df asdf as df asdf as f asdfas
- item 2 asfasdfasdf a sf asdf a sdf as f asdf as f asf aas df asdf as df asdf as f asdfas
    - item 2.1 asfasdfasdf a sf asdf a sdf as f asdf as f asf aas df asdf as df asdf as f asdfas
    - item 2.2 asfasdfasdf a sf asdf a sdf as f asdf as f asf aas df asdf as df asdf as f asdfas
- item 3 asfasdfasdf a sf asdf a sdf as f asdf as f asf aas df asdf as df asdf as f asdfas
- item 4 asfasdfasdf a sf asdf a sdf as f asdf as f asf aas df asdf as df asdf as f asdfas

        Line 1 asfasdfasdf a sf asdf a sdf as f asdf as f asf aas df asdf as df asdf as f asdfas Line 2 asfasdfasdf a sf
        asdf a sdf as f asdf as f asf aas df asdf as df asdf as f asdfas
        - item 1 asfasdfasdf a sf asdf a sdf as f asdf as f asf aas df asdf as df asdf as f asdfas
        - item 2 asfasdfasdf a sf asdf a sdf as f asdf as f asf aas df asdf as df asdf as f asdfas

            - item 2.1 asfasdfasdf a sf asdf a sdf as f asdf as f asf aas df asdf as df asdf as f asdfas
            - item 2.2 asfasdfasdf a sf asdf a sdf as f asdf as f asf aas df asdf as df asdf as f asdfas

    - item 4.1 asfasdfasdf a sf asdf a sdf as f asdf as f asf aas df asdf as df asdf as f asdfas
    - item 4.2 asfasdfasdf a sf asdf a sdf as f asdf as f asf aas df asdf as df asdf as f asdfas

    Line 1 asfasdfasdf a sf asdf a sdf as f asdf as f asf aas df asdf as df asdf as f asdfas Line 2 asfasdfasdf a sf
    asdf a sdf as f asdf as f asf aas df asdf as df asdf as f asdfas

Line 1 asfasdfasdf a sf asdf a sdf as f asdf as f asf aas df asdf as df asdf as f asdfas Line 2 asfasdfasdf a sf asdf a
sdf as f asdf as f asf aas df asdf as df asdf as f asdfas'''

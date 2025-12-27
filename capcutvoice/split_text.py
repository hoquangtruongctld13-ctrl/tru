def split_text(arr_input, max_length):
    arr_lines = []
    temp_lines = ""
    text_seg = ""

    for line in arr_input:
        text_seg += "\n" + line
        if (len(line) + len(temp_lines) + (1 if temp_lines else 0)) < max_length:
            if temp_lines:
                temp_lines += "\n"
            temp_lines += line
        else:
            arr_lines.append(temp_lines)
            temp_lines = line

    if temp_lines:
        arr_lines.append(temp_lines)

    return arr_lines


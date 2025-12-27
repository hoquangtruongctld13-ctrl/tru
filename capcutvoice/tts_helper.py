import re

class TextToSpeechHelper:
    
    class BreakMode:
        Sentence = 0
        Paragraph = 1
        Custom = 2

    class Sentence:
        def __init__(self, text, start, end):
            self.text = text
            self.start = start
            self.end = end

    @staticmethod
    def break_sentence(text, max_length, mode):
        if mode == TextToSpeechHelper.BreakMode.Sentence:
            return TextToSpeechHelper.break_tts_sentence(
                text=text,
                max_length=max_length,
                skip_new_line=False,
                skip_end_sentence=False,
            )
        elif mode == TextToSpeechHelper.BreakMode.Paragraph:
            return TextToSpeechHelper.break_tts_sentence(
                text=text,
                max_length=max_length,
                skip_new_line=False,
                skip_end_sentence=True,
            )
        else:
            return TextToSpeechHelper.break_tts_sentence(
                text=text,
                max_length=max_length,
                skip_new_line=True,
                skip_end_sentence=True,
            )

    @staticmethod
    def break_tts_sentence(text, max_length, skip_new_line, skip_end_sentence):
        sentences = []
        index = 0
        length = len(text)
        start = 0
        last_dot = -1
        last_comma = -1
        last_line = -1
        while index < length:
            c = text[index]

            if not skip_new_line and TextToSpeechHelper.is_new_line(c):
                sentences.append(TextToSpeechHelper.Sentence(
                    text=text[start:index],
                    start=start,
                    end=index,
                ))
                last_line = -1
                last_dot = -1
                last_comma = -1
                start = index + 1
                index += 1
                continue
            else:
                if not skip_end_sentence and TextToSpeechHelper.is_end_sentence(c) and index > start + 5:
                    sentences.append(TextToSpeechHelper.Sentence(
                        text=text[start:index + 1],
                        start=start,
                        end=index + 1,
                    ))
                    last_line = -1
                    last_dot = -1
                    last_comma = -1
                    start = index + 1
                    index += 1
                    continue
                if index - start >= max_length:
                    if skip_new_line and last_line > 0 and last_line - start < max_length and last_line - start > max_length / 3:
                        index = last_line
                    elif last_dot > 0 and last_dot - start < max_length:
                        index = last_dot + 1
                    elif last_comma > 0 and last_comma - start < max_length:
                        index = last_comma + 1
                    else:
                        # Tìm khoảng trống gần nhất trước max_length
                        cut_point = start + max_length - 1
                        while cut_point > start and text[cut_point] != ' ':
                            cut_point -= 1
                        if cut_point > start:
                            index = cut_point + 1
                        else:
                            index = start + max_length
                    sentences.append(TextToSpeechHelper.Sentence(
                        text=text[start:index],
                        start=start,
                        end=index,
                    ))
                    last_line = -1
                    last_dot = -1
                    last_comma = -1
                    start = index
                    continue

            if TextToSpeechHelper.is_new_line(c):
                last_line = index
            if TextToSpeechHelper.is_end_sentence(c):
                last_dot = index
            if TextToSpeechHelper.is_break_char(c):
                last_comma = index
            index += 1

        # Xử lý phần cuối cùng với kiểm tra bổ sung
        if start < length:
            last_part = text[start:length].strip()
            if len(last_part) <= 5:  # Kiểm tra nếu dưới 5 ký tự
                if not last_part or not re.search(r'[a-zA-Z0-9À-ỹ]', last_part) or last_part in ['"', ' ', '" ', ' "']:
                    print(f"Skipping last part of chunk: Meaningless content detected ('{last_part}')")
                else:
                    sentences.append(TextToSpeechHelper.Sentence(
                        text=last_part,
                        start=start,
                        end=length,
                    ))
            else:
                sentences.append(TextToSpeechHelper.Sentence(
                    text=last_part,
                    start=start,
                    end=length,
                ))

        return [sentence for sentence in sentences if sentence.text.strip()]

    END_CHARS = {'.', '!', ':', '?', '…', '。', '？', '！'}
    BREAK_CHARS = {',', ';', '，', '、'}

    @staticmethod
    def is_end_sentence(char):
        return char in TextToSpeechHelper.END_CHARS

    @staticmethod
    def is_break_char(char):
        return char in TextToSpeechHelper.BREAK_CHARS

    @staticmethod
    def is_new_line(char):
        return char == '\n'
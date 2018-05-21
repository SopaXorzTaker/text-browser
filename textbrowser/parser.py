import html

EMPTY_ELEMENTS = ["area", "base", "br", "col", "hr", "img", "input", "link", "meta", "param", "li", "hr",
                  "source", "track", "wbr"]

IGNORED_ELEMENTS = ["script", "style", "svg", "iframe"]


class Token(object):
    """
    A token for the parser.
    """

    def __init__(self, *args, **kwargs):
        pass

    @classmethod
    def parse(cls, text):
        pass


class TextToken(Token):
    """
    A token for raw text.
    """

    def __init__(self, text, *args, **kwargs):
        """
        Initialized this TextToken object
        :param text: the text
        """
        super().__init__(*args, **kwargs)
        self.text = text

    @classmethod
    def parse(cls, text):
        """
        Parses text for the token
        :param text: the text to parse
        :return: the TextToken
        """

        return cls(text)

    def __repr__(self):
        return "<TextToken: %s>" % self.text


class HTMLTag(Token):
    """
    An HTML tag token.
    """

    def __init__(self, name, is_closed, is_closing, attributes, *args, **kwargs):
        """
        Initializes this HTMLTag object
        :param raw_tag: the raw tag this tag was decoded from
        :param name: the tag name
        :param is_closed: whether the tag is closed
        :param is_closing: whether the tag is a closing one
        :param attributes: the tag attributes
        """

        super().__init__(*args, **kwargs)
        self.name, self.is_closed, self.is_closing, self.attributes = name, is_closed, is_closing, attributes

    @classmethod
    def parse(cls, text):
        """
        Parses a given tag
        :param text: the text to parse a tag from
        :return: the parsed HTMLTag
        """

        is_closed = False
        is_closing = False
        attributes = {}

        text = text.strip()

        if text.startswith("/"):
            is_closing = True
            text = text[1:]

        if text.endswith("/"):
            is_closed = True
            text = text[:-1]

        tag_name = text.split(" ")[0].strip().lower().replace("\t", "")

        if " " in text:
            text = text[text.index(" ") + 1:]
        else:
            text = ""

        key = ""
        value = ""
        value_started = False
        escape_character = None

        for i, char in enumerate(text):
            if not value_started:
                if char == "=":
                    value_started = True
                elif not char == " ":
                    key += char
                else:
                    key = ""
                    if key:
                        attributes[key.strip().lower()] = key.strip().lower()
                        key = ""
            else:
                if i == len(text) - 1 and not escape_character:
                    value += char

                if char == escape_character or (escape_character is None and char in [" ", "/"]) or i == len(text) - 1:
                    attributes[key.strip().lower()] = html.unescape(value)
                    key = ""
                    value = ""
                    value_started = False
                    escape_character = None

                elif char in ["'", "\""]:
                    escape_character = char

                else:
                    value += char

        return cls(tag_name, is_closed, is_closing, attributes)

    def __repr__(self):
        return "<HTMLTag %s is_closed: %r, is_closing: %r, attributes: %r>" % (self.name, self.is_closed,
                                                                               self.is_closing, self.attributes)


class HTMLElement(object):
    """
    An HTML element.
    """

    def __init__(self, is_text, name="", text="", attributes=None, inner_elements=None):
        """
        Initializes this HTMLElement object
        :param is_text: whether this element is a text one
        :param name: the name of this element
        :param text: the inner text
        :param attributes: the attributes of this element
        :param inner_elements: the inner elements of this element
        """

        if not attributes:
            attributes = {}

        if not inner_elements:
            inner_elements = []

        self.is_text, self.name, self.text, self.attributes, self.inner_elements =\
            is_text, name, text, attributes, inner_elements

    def __repr__(self):
        if self.is_text:
            return "<HTMLElement text: %s>" % self.text
        else:
            return "<HTMLElement name: %s, attributes: %r, inner_elements: %r>" %\
                   (self.name, self.attributes, self.inner_elements)


class HTMLParser(object):
    """
    An HTML parser that extracts the HTML elements from input text.

    """

    @staticmethod
    def parse(text):
        """
        Parses given text
        :param text: the text to be parsed
        :return: a list of elements
        """

        tag_started = False
        comment = False
        tag = ""
        raw_text = ""
        comment_text = ""

        tokens = []

        # Handle CRLF
        text = text.replace("\r", "")

        for char in text:
            if not tag_started:
                # Tag start
                if char == "<":
                    tag_started = True

                    if raw_text.strip():
                        tokens.append(TextToken.parse(raw_text))

                    raw_text = ""
                elif comment:
                    comment_text += char

                    if (comment_text.startswith("DOCTYPE") and comment_text.endswith(">")) or\
                            comment_text.endswith("-->"):
                        comment_text = ""
                        comment = False
                else:
                    raw_text += char
            else:
                if len(raw_text) == 0 and char == "!":
                    comment = True
                    tag_started = False
                elif char == ">":
                    tag = tag.replace("\n", " ")

                    if tag.strip()[0] not in ["!", "?"]:
                        tokens.append(HTMLTag.parse(tag))

                    tag = ""
                    tag_started = False
                elif char == "<":
                    tag = ""
                else:
                    tag += char

        elements = []

        current_element = None

        prev_elements = []
        inner_elements = elements
        ignored_element = None

        for token in tokens:
            if isinstance(token, HTMLTag):
                if token.is_closing and token.name not in EMPTY_ELEMENTS:
                    if ignored_element:
                        if token.name == ignored_element:
                            ignored_element = None
                    else:
                        if current_element:
                            last_open_tag = current_element.name
                        else:
                            last_open_tag = None

                        if not token.name == last_open_tag:
                            print("Error: unexpected closing tag for", current_element.name, token.name)
                            continue

                        current_element = prev_elements.pop()

                        if current_element:
                            inner_elements = current_element.inner_elements
                        else:
                            inner_elements = elements
                else:
                    element = HTMLElement(False, name=token.name, attributes=token.attributes)

                    if ignored_element is None:
                        if element.name not in IGNORED_ELEMENTS:
                            inner_elements.append(element)

                            if not token.is_closed and token.name not in EMPTY_ELEMENTS:
                                prev_elements.append(current_element)
                                current_element = element
                                inner_elements = current_element.inner_elements
                        else:
                            ignored_element = element.name
            elif not ignored_element:
                element = HTMLElement(True, text=token.text)
                inner_elements.append(element)

        if prev_elements:
            print("Error: some tags weren't closed!")
        return elements

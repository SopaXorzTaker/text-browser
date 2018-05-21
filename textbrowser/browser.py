import html
import urllib.parse
import urllib.request

from textbrowser.parser import *


class FormInput(object):
    def __init__(self, name, input_type, default_value, select_options=None):
        if select_options is None:
            select_options = []

        self.name, self.input_type, self.value, self.options = \
            name, input_type, default_value, select_options


class Form(object):
    def __init__(self, action, method):
        self.action = action
        self.method = method
        self.inputs = {}

    def add_input(self, name, input_type, value):
        if input_type not in ["button", "submit"]:
            self.inputs[name] = FormInput(name, input_type, value)

    def add_select(self, name, value, options):
        self.inputs[name] = FormInput(name, "select", value, options)

    def set_input(self, name, value):
        self.inputs[name].value = value

    def get_inputs(self):
        return self.inputs.values()


class Browser(object):
    def __init__(self, url=None):
        self.url = None
        self.hyperlinks = []
        self.forms = []
        self.page = None
        self.rendered = ""

        if url:
            self.go(url)

    def go(self, url, data=None):
        print("Loading %s..." % url)
        if not (url.startswith("http://") or url.startswith("https://")):
            url = "http://" + url

        self.url = url

        try:
            response = urllib.request.urlopen(url, data=data)
            self.page = response.read().decode("utf-8", errors="replace")

            old_url = self.url
            self.url = response.geturl()

            if not old_url == self.url:
                print("Redirect: ", self.url)

            self.process()
        except Exception as ex:
            print("Error loading the page: %r" % ex)

        stop = False
        while not stop:
            command = input("Type address or hyperlink/form index (or 'help'): ")

            if command == "help":
                print()
                print("Navigation help")
                print("Enter a hyperlink index (e.g. 1) to follow it.")
                print("Enter a form index starting from # to edit it and ! to submit (e.g. #0 or !5).")
            elif command[0] not in ["!", "#"]:
                try:
                    hyperlink_index = int(command, 10)
                    if hyperlink_index < len(self.hyperlinks):
                        self.go(self.hyperlinks[hyperlink_index])
                    else:
                        print("Invalid hyperlink index!")
                except ValueError:
                    stop = True
                    self.go(command)
            else:
                form_index = int(command[1:], 10)

                if form_index < len(self.forms):
                    form = self.forms[form_index]

                    if command[0] == "#":
                        print("Editing form %d" % form_index)
                        print("Available inputs:")

                        available_inputs = []

                        for form_input in form.get_inputs():
                            if form_input.input_type not in ["button", "submit", "hidden"]:
                                if not form_input.input_type == "select":
                                    print("| %s <%s> [%s]" % (form_input.name, form_input.input_type, form_input.value))
                                else:
                                    print("| %s <select>" % form_input.name)

                                    allowed_values = []

                                    for value, text in form_input.options:
                                        if value == form_input.value:
                                            print("-> * %s [%s]" % (text, value))
                                        else:
                                            print("-> . %s [%s]" % (text, value))

                                        allowed_values.append(value)

                                available_inputs.append(form_input.name)

                        input_name = None

                        while input_name not in available_inputs:
                            input_name = input("Input name: ")

                            if not input_name:
                                break

                        if input_name:
                            available_values = None
                            form_input = self.forms[form_index].inputs[input_name]

                            if form_input.input_type == "select":
                                available_values = [k for k, v in form_input.options]

                            input_value = None

                            while available_values and input_value not in available_values:
                                input_value = input("Value: ")

                            self.forms[form_index].set_input(input_name, input_value)
                    else:
                        form = self.forms[form_index]
                        action = form.action

                        input_values = {}
                        for form_input in form.get_inputs():
                            if not (not form_input.value and form_input.input_type == "checkbox"):
                                input_values[form_input.name] = form_input.value

                        params = urllib.parse.urlencode([(k, v) for k, v in input_values.items()])

                        if form.method == "get":
                            action += "?" + params
                            self.go(action)
                        else:
                            self.go(action, params.encode("utf-8"))

    def process(self):
        print("\x1bc")

        try:
            elements = HTMLParser.parse(self.page)
            self.render(elements)
            print(self.rendered)
        except Exception as ex:
            print("Couldn't parse the page: %r" % ex)

    def register_hyperlink(self, url):
        self.hyperlinks.append(urllib.parse.urljoin(self.url, url))
        return len(self.hyperlinks) - 1

    def register_form(self, form):
        form.action = urllib.parse.urljoin(self.url, form.action)
        self.forms.append(form)
        return len(self.forms) - 1

    def render(self, elements, initial=True):
        if initial:
            self.rendered = ""
            self.hyperlinks = []
            self.forms = []

        for element in elements:
            self.render_element(element)

    def render_element(self, element):
        # For any HTML element, simply render its internals
        if isinstance(element, HTMLElement):
            prefix = ""
            suffix = ""

            if not element.is_text:
                if element.name == "a":
                    title = element.attributes.get("title", "")

                    if "href" in element.attributes:
                        hyperlink_index = self.register_hyperlink(element.attributes["href"])
                        if title:
                            prefix = " \x1b[34m\x1b[1mHyperlink [%d] \x1b[21m\x1b[39m <%s>" % (hyperlink_index, title)
                        else:
                            prefix = " \x1b[34m\x1b[1mHyperlink [%d] \x1b[21m\x1b[39m<" % hyperlink_index
                            suffix = "> "
                    else:
                        prefix = " \x1b[34m\x1b[1mHyperlink: \x1b[21m\x1b[39m<"
                        suffix = "> "
                elif element.name == "title":
                    prefix = "\x1b[36mDocument Title: \x1b[0m"
                    suffix = "\n"
                elif element.name in ["b", "strong", "em"]:
                    prefix = "\x1b[1m"
                    suffix = "\x1b[21m"
                elif element.name in ["h1", "h2", "h3", "h4"]:
                    prefix = "\x1b[1m"
                    suffix = "\x1b[21m\n"
                elif element.name == "i":
                    prefix = "\x1b[3m"
                    suffix = "\x1b[23m"
                elif element.name == "u":
                    prefix = "\x1b[4m"
                    suffix = "\x1b[24m"
                elif element.name in ["s", "strike"]:
                    prefix = "\x1b[9m"
                    suffix = "\x1b[29m"
                elif element.name in ["ul", "ol", "br", "p", "td"]:
                    suffix = "\n"
                elif element.name == "div":
                    prefix = "\n"
                    suffix = "\n"
                elif element.name in ["span", "tr"]:
                    prefix = "\t"
                elif element.name == "li":
                    prefix = "\n* "
                elif element.name == "img":
                    if "alt" in element.attributes and element.attributes["alt"]:
                        prefix = " \x1b[32m\x1b[1mImage [%s]\x1b[21m\x1b[39m " % \
                                 html.unescape(element.attributes["alt"])
                    else:
                        prefix = " \x1b[32m\x1b[1mImage\x1b[21m\x1b[39m "

                if element.name == "form":
                    self.render_form(element)
                else:
                    self.rendered += prefix
                    self.render(element.inner_elements, False)
                    self.rendered += suffix
            else:
                line = html.unescape(element.text.replace("\n", "").replace("\t", ""))

                broken_line = ""
                line_len = 0

                for char in line:
                    if char == "\n":
                        line_len = 0

                    if line_len == 80:
                        broken_line += "\n"
                        line_len = 0

                    broken_line += char
                    line_len += 1

                self.rendered += broken_line

            if "\n" in self.rendered:
                last_break = self.rendered[::-1].index("\n")
            else:
                last_break = 0

            if last_break > 80:
                self.rendered += "\n"

    def render_form(self, element, initial=True, current_form=None):
        if initial:
            action = element.attributes.get("action", "")
            method = element.attributes.get("method", "get").lower()

            current_form = Form(action, method)

            # Render the form differently if one can't submit it
            if "action" in element.attributes:
                prefix = "\n\x1b[36m\x1b[1m---- Form [#%d] ----\x1b[21m\x1b[39m\n" % \
                         len(self.forms)
            else:
                prefix = "\n\x1b[36m\x1b[1m---- Form ----\x1b[21m\x1b[39m\n"

            suffix = "\n\x1b[36m\x1b[1m---- End form ----\x1b[21m\x1b[39m\n"

            self.rendered += prefix
            self.render_form(element, False, current_form)
            self.rendered += suffix

            self.register_form(current_form)
        else:
            for inner_element in element.inner_elements:
                if inner_element.name == "input":
                    input_name = inner_element.attributes.get("name", "")
                    input_type = inner_element.attributes.get("type", "")
                    input_value = inner_element.attributes.get("value", "")

                    if input_type == "checkbox" and "checked" in inner_element.attributes:
                        input_value = input_name

                    if input_name:
                        current_form.add_input(input_name, input_type, input_value)

                    if not input_type == "hidden":
                        if not input_type == "checkbox":
                            if input_name:
                                self.rendered += "\x1b[35m\x1b[1mInput [%s: %s]\x1b[21m\x1b[39m\n" %\
                                                 (input_name, input_type)
                            else:
                                self.rendered += "\x1b[35m\x1b[1mInput [%s]\x1b[21m\x1b[39m\n" % input_type
                        else:
                            if input_value:
                                self.rendered += "\x1b[35m\x1b[1mCheckbox [%s] [x]\x1b[21m\x1b[39m\n" % input_name
                            else:
                                self.rendered += "\x1b[35m\x1b[1mCheckbox [%s] [ ]\x1b[21m\x1b[39m\n" % input_name
                elif inner_element.name == "select":
                    input_name = inner_element.attributes.get("name", "")
                    input_value = inner_element.attributes.get("value", "")

                    self.rendered += "\n\x1b[33m\x1b[1m---- Select ----\x1b[21m\x1b[39m\n"

                    # Handle the select options
                    options = []

                    for option_element in inner_element.inner_elements:
                        option_value = html.unescape(option_element.attributes.get("value", ""))
                        option_text = ""

                        # Extract the option text
                        for option_inner in option_element.inner_elements:
                            if option_inner.is_text:
                                option_text += html.unescape(option_inner.text)

                        option_text = option_text.strip().replace("\n", "")
                        options.append((option_value, option_text))

                        if option_value == input_value:
                            self.rendered += "\x1b[33m* %s [%s]\x1b[39m\n" % (option_text, option_value)
                        else:
                            self.rendered += "\x1b[33m. %s [%s]\x1b[39m\n" % (option_text, option_value)

                    current_form.add_select(input_name, input_value, options)
                    self.rendered += "\x1b[33m\x1b[1m---- End select ----\x1b[21m\x1b[39m\n"

                else:
                    self.render_element(inner_element)
                    self.render_form(inner_element, False, current_form)

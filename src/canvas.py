from pyscript import when, display


@when("click", "#clickMe")
def handler():
    display("Button clicked!")
from pykrx import stock
import inspect

def list_functions():
    functions = inspect.getmembers(stock, inspect.isfunction)
    for name, func in functions:
        if "purchase" in name or "buy" in name or "sell" in name or "net" in name:
            print(name)

if __name__ == "__main__":
    list_functions()

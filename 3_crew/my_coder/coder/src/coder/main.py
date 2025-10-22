#!/usr/bin/env python
import sys
import warnings

from datetime import datetime

from coder.crew import Coder

warnings.filterwarnings("ignore", category=SyntaxWarning, module="pysbd")


assignment = "Write a python program to make an API that talks to the backend of a pizza ordering app"

def run():
    inputs = {
        "assignment": assignment
    }
    result = Coder().crew().kickoff(inputs=inputs)
    print(result.raw)
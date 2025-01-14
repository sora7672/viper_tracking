"""
This module provides utilities for evaluating and applying conditions on objects.

Features:
- Validates attributes of objects against dynamic conditions.
- Supports common comparison operators like `==`, `!=`, `<`, `>`, `<=`, `>=`.
- Supports nested conditions through logical operators (e.g., 'and', 'or').
- Provides helper functions for creating and applying conditions programmatically.

Author: sora7672
"""
__author__ = 'sora7672'

from datetime import datetime, date, time, timedelta
import json
from threading import Lock


class ObjectCondition:
    """
    Represents a single condition to evaluate an attribute of an object.

    This class allows checking if an object's attribute satisfies a condition
    defined by a comparison operator and value.
    """

    _accepted_comp_operators_strings = ("==", "!=", "in", "not in")
    _accepted_comp_operators_numbers = ("<", ">", "<=", ">=", "==", "!=")
    _accepted_comp_operators_lists = ("in", "not in")
    _accepted_comp_operators = tuple(set(_accepted_comp_operators_strings +
                                         _accepted_comp_operators_numbers +
                                         _accepted_comp_operators_lists))
    # TODO: add weekdays, months to compare & also allow == and != for these, add validation rules for that too!
    #  and check only all lowercase to ensure no caps/lower typos
    _accepted_value_types = ("str", "int", "float", "date", "datetime", "time")

    def __init__(self, attribute_name: str, comp_operator: str,
                 attribute_value: str | int | float | date | datetime | time, value_type: str = "str"):
        """
        Initializes an ObjectCondition instance with a specified attribute, comparison operator, value, and value type.

        :param attribute_name: str (Name of the attribute to be evaluated on the object.)
        :param comp_operator: str (Comparison operator, must be one of the accepted types.)
        :param attribute_value: Any (The value to compare against.)
        :param value_type: str (The type of the attribute, default is 'str'.)
        :raises ValueError: If the value type or comparison operator is invalid.
        """

        if value_type not in self._accepted_value_types:
            raise ValueError(f"Value type {value_type} is not accepted. Accepted types: {self._accepted_value_types}")
        if comp_operator not in self._accepted_comp_operators:
            raise ValueError("Comp operators not supported")

        self._value_type = value_type
        self._comp_operator: str = comp_operator
        self._attribute_name: str = attribute_name

        match value_type:
            case "str":
                if self._comp_operator not in self._accepted_comp_operators_strings:
                    raise ValueError(f"Comp operator {self._comp_operator} not supported for strings")
                self._attribute_value = str(attribute_value)

            case "int":
                if self._comp_operator not in self._accepted_comp_operators_numbers:
                    raise ValueError(f"Comp operator {self._comp_operator} not supported for numbers")
                self._attribute_value = int(attribute_value)

            case "float":
                if self._comp_operator not in self._accepted_comp_operators_numbers:
                    raise ValueError(f"Comp operator {self._comp_operator} not supported for numbers")
                self._attribute_value = float(attribute_value)

            case "date":
                if self._comp_operator not in self._accepted_comp_operators_numbers:
                    raise ValueError(f"Comp operator {self._comp_operator} not supported for numbers")
                self._attribute_value = self.parse_datetime(attribute_value).date()

            case "time":
                if self._comp_operator not in self._accepted_comp_operators_numbers:
                    raise ValueError(f"Comp operator {self._comp_operator} not supported for numbers")
                self._attribute_value = self.parse_datetime(attribute_value).time()

            case "datetime":
                if self._comp_operator not in self._accepted_comp_operators_numbers:
                    raise ValueError(f"Comp operator {self._comp_operator} not supported for numbers")
                self._attribute_value = self.parse_datetime(attribute_value)

            case _:
                raise ValueError(f"Invalid value type {value_type}")


        self.lock = Lock()

    @property
    def attribute_name(self) -> str:
        with self.lock:
            return self._attribute_name

    @property
    def comp_operator(self) -> str:
        with self.lock:
            return self._comp_operator

    @property
    def attribute_value(self) -> str:
        with self.lock:
            return str(self._attribute_value)

    def is_true(self, obj: object) -> bool:
        """
        Evaluates the condition on a given object.

        :param obj: object (The object containing the attribute to evaluate.)
        :return: bool (True if the condition is satisfied, False otherwise.)
        :raises AttributeError: If the attribute does not exist on the object.
        :raises TypeError: If the attribute type does not match the expected value type.
        :raises Exception: If the comparison operator is unknown.
        """

        if not hasattr(obj, self._attribute_name):
            raise AttributeError(f"Condition evaluation error.\nObject ({obj}) has no attribute {self._attribute_name}")

        test_value = getattr(obj, self._attribute_name)

        if self._value_type == "str":
            if not isinstance(test_value, (str, tuple, list, set, frozenset)):
                raise TypeError(f"Condition evaluation error.\nObject ({obj}) attribute type {type(test_value)} "
                                f"is not type (str, tuple, list, set, frozenset)")
        elif self._value_type in ("date", "time", "datetime"):
            test_value = self.convert_to_type(test_value)

        elif not isinstance(test_value, type(self._attribute_value)):
            raise TypeError(f"Condition evaluation error.\nObject ({obj}) attribute type {type(test_value)} "
                            f"is not type {type(self._attribute_value)}")

        match self._comp_operator:
            case "in":
                if isinstance(test_value, str):
                    return self._attribute_value.lower() in test_value.lower()
                else:
                    return self._attribute_value.lower() in [item.lower() for item in test_value]

            case "not in":
                if isinstance(test_value, str):
                    return self._attribute_value.lower() not in test_value.lower()
                else:
                    return self._attribute_value.lower() not in [item.lower() for item in test_value]

            case "<":
                return self._attribute_value < test_value

            case ">":
                return self._attribute_value > test_value

            case "<=":
                return self._attribute_value <= test_value

            case ">=":
                return self._attribute_value >= test_value

            case "==":
                if isinstance(test_value, str):
                    return test_value.lower() == self._attribute_value.lower()
                else:
                    return test_value == self._attribute_value

            case "!=":
                if isinstance(test_value, str):
                    return test_value.lower() != self._attribute_value.lower()
                else:
                    return test_value != self._attribute_value

            case _:
                raise Exception(f"Unknown comparison operator {self._comp_operator}")

    def to_dict(self) -> dict:
        """
        Serializes the condition to a dictionary format.

        :return: dict (A dictionary representation of the condition.)
        """

        with self.lock:
            return {
                "attribute_name": self._attribute_name,
                "comp_operator": self._comp_operator,
                "attribute_value": str(self._attribute_value),
                "value_type": self._value_type
            }

    def json(self) -> str:
        """
        Serializes the condition to a JSON string.

        :return: str (A JSON string representation of the condition.)
        """

        return json.dumps(self.to_dict())

    def convert_to_type(self, input_value) -> datetime | date | time:
        """
        Converts an input value to the type specified by the condition.

        :param input_value: Any (The value to convert.)
        :return: Any (The converted value in the specified type.)
        :raises ValueError: If the input is not valid for the specified type.
        :raises TypeError: If the input type is unsupported.
        """

        # Ensure output_type is valid
        # Convert input_value to a datetime object first
        if isinstance(input_value, datetime):
            # Already a datetime, so no conversion needed
            dt_value = input_value
        elif isinstance(input_value, date):
            # Convert date to datetime at midnight
            dt_value = datetime.combine(input_value, time(0, 0))
        elif isinstance(input_value, time):
            # Convert time to datetime on today's date
            dt_value = datetime.combine(date.today(), input_value)
        elif isinstance(input_value, (int, float)):
            # Treat as Unix timestamp
            dt_value = datetime.fromtimestamp(input_value)
        elif isinstance(input_value, str):
            # Try to parse string as ISO format datetime or date
            try:
                dt_value = datetime.fromisoformat(input_value)
            except ValueError:
                try:
                    # If input is date-only format
                    dt_value = datetime.combine(date.fromisoformat(input_value), time(0, 0))
                except ValueError:
                    raise ValueError("String format not recognized as ISO date or datetime.")
        else:
            raise TypeError("Unsupported input type. Must be date, time, datetime, float, or string.")

        # Convert dt_value to the requested output type
        if self._value_type == "date":
            return dt_value.date()
        elif self._value_type == "time":
            return dt_value.time()
        elif self._value_type == "datetime":
            return dt_value

    @classmethod
    def from_json(cls, data: str | dict) -> 'ObjectCondition':
        """
        Creates an ObjectCondition instance from a JSON string or dictionary.

        :param data: dict | str (A dictionary or JSON string containing the condition parameters.)
        :return: ObjectCondition (The constructed ObjectCondition instance.)
        """

        if isinstance(data, str):
            data = json.loads(data)
        elif not isinstance(data, dict):
            raise ValueError("Input must be a JSON string or a dictionary.")

        return cls(
            attribute_name=data["attribute_name"],
            comp_operator=data["comp_operator"],
            attribute_value=data["attribute_value"],
            value_type=data["value_type"]
        )

    @classmethod
    def get_operators_for_string(cls):
        return cls._accepted_comp_operators_strings

    @classmethod
    def get_operators_for_number(cls):
        return cls._accepted_comp_operators_numbers

    @staticmethod
    def parse_datetime(value: str) -> datetime:
        """
        Parses a date/time from string or timestamp.
        :param value: string with timestamp or date.
        :return: datetime object representing the given value.
        """
        if value.replace('.', '', 1).isdigit():
            timestamp = float(value)
            return datetime.fromtimestamp(timestamp)
        elif "-" in value and ("T" in value or len(value) == 10):
            if len(value) == 10:
                return datetime.fromisoformat(value + "T00:00:00")
            else:
                return datetime.fromisoformat(value)
        else:
            raise ValueError("Input is not a recognized Unix timestamp or ISO datetime format.")

    def __str__(self) -> str:
        return f"Condition on {self._attribute_name} {self._comp_operator} {self._attribute_value} ({self._value_type})"


class ConditionList:
    """
    Represents a collection of ObjectCondition and ConditionList objects combined using a logical operator.

    Allows for grouping multiple conditions with 'and' or 'or' logic.
    """

    _accepted_boolean_operators = ("and", "or")

    def __init__(self, *conditions, operator: str = "and"):
        """
        Initializes a ConditionList with specified conditions and logical operator.

        :param conditions: list (A list of ObjectCondition or ConditionList instances to evaluate.)
        :param operator: str (Logical operator for combining conditions, must be 'and' or 'or'.)
        :raises ValueError: If the operator or condition type is invalid.
        """

        self.conditions = []
        self.lock = Lock()
        if operator.lower() not in self._accepted_boolean_operators:
            raise ValueError("Operator not supported")
        self.operator = operator.lower()

        for condition in conditions:
            if isinstance(condition, ObjectCondition) or isinstance(condition, ConditionList):
                self.conditions.append(condition)
            else:
                raise ValueError(f"Invalid condition type {type(condition)}")

    def add(self, *conditions):
        """
        Adds conditions to the ConditionList.

        :param conditions: list (A list of ObjectCondition or ConditionList instances to add.)
        :raises ValueError: If a condition type is invalid.
        """

        with self.lock:
            for condition in conditions:
                if isinstance(condition, ObjectCondition) or isinstance(condition, ConditionList):
                    self.conditions.append(condition)
                else:
                    raise ValueError(f"Invalid condition type {type(condition)}")

    def is_true(self, obj: object) -> bool:
        """
        Evaluates all conditions in the list using the logical operator.

        :param obj: object (The object to evaluate conditions on.)
        :return: bool (True if all conditions are satisfied according to the operator.)
        """

        result_list = []
        for condition in self.conditions:
            result = condition.is_true(obj)
            result_list.append(result)


        final_result = result_list[0]
        for result in result_list[1:]:
            if self.operator == "and":
                final_result = final_result and result
            elif self.operator == "or":
                final_result = final_result or result
            else:
                raise ValueError(f"Unknown operator: {self.operator}")

        return final_result

    def to_dict(self) -> dict:
        """
        Serializes the ConditionList to a dictionary format.

        :return: dict (A dictionary representation of the ConditionList.)
        """

        return {
            "operator": self.operator,
            "conditions": [condition.to_dict() for condition in self.conditions]
        }

    def json(self) -> str:
        """
        Serializes the ConditionList to a JSON string.

        :return: str (A JSON string representation of the ConditionList.)
        """

        return json.dumps(self.to_dict())

    @classmethod
    def from_json(cls, data: str | dict) -> 'ConditionList':
        """
        Creates a ConditionList instance from a JSON string or dictionary.

        :param data: dict | str (A dictionary or JSON string containing 'operator' and 'conditions'.)
        :return: ConditionList (The constructed ConditionList instance.)
        """

        if isinstance(data, str):
            data = json.loads(data)
        elif not isinstance(data, dict):
            raise ValueError("Input must be a JSON string or a dictionary.")

        operator = data.get("operator", "and")
        conditions = [
            ObjectCondition.from_json(cond) if isinstance(cond, dict) and "attribute_name" in cond else cls.from_json(
                cond)
            for cond in data.get("conditions", [])
        ]

        return cls(*conditions, operator=operator)

    def __str__(self) -> str:
        conditions_str = f" {self.operator.upper()} ".join(str(cond) for cond in self.conditions)
        return f"ConditionList({conditions_str})"

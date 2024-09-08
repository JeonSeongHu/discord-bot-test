from enum import Enum
from typing import List, Dict, Any
from datetime import datetime, timedelta
import dateparser
from pprint import pprint


# Enum for Filter Types based on Notion data types
class FilterType(Enum):
    CHECKBOX = "checkbox"
    TEXT = "rich_text"
    DATE = "date"
    NUMBER = "number"
    MULTI_SELECT = "multi_select"
    TITLE = "title"

# Enum for Operator Types
class Operator(Enum):
    EQUALS = "equals"
    CONTAINS = "contains"
    LESS_THAN = "less_than"
    LESS_THAN_OR_EQUAL = "less_than_or_equal_to"
    GREATER_THAN = "greater_than"
    GREATER_THAN_OR_EQUAL = "greater_than_or_equal_to"
    IS_EMPTY = "is_empty"
    IS_NOT_EMPTY = "is_not_empty"
    NOT_EQUALS = "not_equals"

class DateOperator(Enum):
    AFTER = "after"
    BEFORE = "before"
    EQUALS = "equals"
    IS_EMPTY = "is_empty"
    IS_NOT_EMPTY = "is_not_empty"
    NOT_EQUALS = "not_equals"
    ON_OR_AFTER = "on_or_after"
    ON_OR_BEFORE = "on_or_before"

operator_map = {
    "=": Operator.EQUALS,
    "!=": Operator.NOT_EQUALS,
    "contains": Operator.CONTAINS,
    "<": Operator.LESS_THAN,
    "<=": Operator.LESS_THAN_OR_EQUAL,
    ">": Operator.GREATER_THAN,
    ">=": Operator.GREATER_THAN_OR_EQUAL,
    "empty": Operator.IS_EMPTY,
    "not empty": Operator.IS_NOT_EMPTY
}

# Supported Date operators map
date_operator_map = {
    ">": DateOperator.AFTER,
    "<": DateOperator.BEFORE,
    "=": DateOperator.EQUALS,
    "is empty": DateOperator.IS_EMPTY,
    "is not empty": DateOperator.IS_NOT_EMPTY,
    "!=": DateOperator.NOT_EQUALS,
    "<=": DateOperator.ON_OR_BEFORE,
    ">=": DateOperator.ON_OR_AFTER,
}

# Mapping natural language time expressions to specific date ranges
def resolve_natural_language_time(expression: str):
    now = datetime.now()

    if expression == "today":
        return now.date().isoformat(), now.date().isoformat()

    if expression == "yesterday":
        yesterday = now - timedelta(days=1)
        return yesterday.date().isoformat(), yesterday.date().isoformat()

    if expression == "this week":
        start_of_week = now - timedelta(days=now.weekday())  # Monday of this week
        end_of_week = start_of_week + timedelta(days=6)  # Sunday of this week
        return start_of_week.date().isoformat(), end_of_week.date().isoformat()

    if expression == "next week":
        start_of_next_week = now + timedelta(days=(7 - now.weekday()))
        end_of_next_week = start_of_next_week + timedelta(days=6)
        return start_of_next_week.date().isoformat(), end_of_next_week.date().isoformat()

    if expression == "last week":
        start_of_last_week = now - timedelta(days=(7 + now.weekday()))
        end_of_last_week = start_of_last_week + timedelta(days=6)
        return start_of_last_week.date().isoformat(), end_of_last_week.date().isoformat()

    if expression == "this month":
        start_of_month = now.replace(day=1)
        next_month = now.replace(day=28) + timedelta(days=4)
        end_of_month = next_month - timedelta(days=next_month.day)
        return start_of_month.date().isoformat(), end_of_month.date().isoformat()

    if expression == "last month":
        start_of_last_month = (now.replace(day=1) - timedelta(days=1)).replace(day=1)
        end_of_last_month = now.replace(day=1) - timedelta(days=1)
        return start_of_last_month.date().isoformat(), end_of_last_month.date().isoformat()

    if expression == "next month":
        next_month = (now.replace(day=28) + timedelta(days=4)).replace(day=1)
        end_of_next_month = (next_month.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)
        return next_month.date().isoformat(), end_of_next_month.date().isoformat()

    # Parse specific dates or datetime formats (e.g., "2024-02-02" or "2021-05-10T12:00:00")
    parsed_date = dateparser.parse(expression,settings={'DATE_ORDER': 'YMD'})
    if parsed_date:
        return parsed_date.date().isoformat(), parsed_date.isoformat()

    raise ValueError(f"Invalid date or time expression: {expression}")


class Condition:
    def __init__(self, db_metadata: Dict[str, Any]):
        self.db_metadata = db_metadata
        self.filters: List[Dict[str, Any]] = []

    def __call__(self, conditions: Dict[str, Any]) -> 'Condition':
        new_condition = Condition(self.db_metadata)
        new_condition.filters = self.parse_conditions(conditions)
        return new_condition

    def parse_conditions(self, conditions: Dict[str, Any]) -> List[Dict[str, Any]]:
        filters = []
        for property_name, condition in conditions.items():
            if property_name not in self.db_metadata:
                raise ValueError(f"Property '{property_name}' not found in database metadata.")

            property_meta = self.db_metadata[property_name]
            filter_type = self.get_filter_type(property_meta['type'])

            filters.extend(self.parse_condition(property_name, filter_type, condition))

        return filters

    def get_filter_type(self, property_type: str) -> FilterType:
        try:
            return FilterType(property_type)
        except ValueError:
            raise ValueError(f"Unsupported property type '{property_type}'")

    def parse_condition(self, property_name: str, filter_type: FilterType, condition: str) -> List[Dict[str, Any]]:
        if filter_type == FilterType.DATE:
            return self.parse_date_conditions(property_name, condition)
        
        operator, value = self.extract_operator_and_value(condition, filter_type)
        return [self.create_filter(property_name, filter_type, operator, value)]

    def parse_date_conditions(self, property_name: str, condition: str) -> List[Dict[str, Any]]:
        """
        Parse date conditions into separate filters for start and end dates if necessary.
        Supports operators like >, <, =, !=, is empty, and is not empty.
        """
        try:
            # Try resolving natural language time (e.g., 'this year', 'next week', etc.)
            start_date, end_date = resolve_natural_language_time(condition)
            filters = []

            # Handling natural language expressions like "this year"
            if start_date and end_date:
                if condition.startswith(">"):
                    filters.append(self.create_date_filter(property_name, DateOperator.ON_OR_AFTER, start_date))
                elif condition.startswith("<"):
                    filters.append(self.create_date_filter(property_name, DateOperator.ON_OR_BEFORE, end_date))
                else:
                    filters.append(self.create_date_filter(property_name, DateOperator.ON_OR_AFTER, start_date))
                    filters.append(self.create_date_filter(property_name, DateOperator.ON_OR_BEFORE, end_date))

            else:
                # Handling specific date operators (e.g., !=, =, is empty, is not empty, >, <)
                operator, value = self.extract_date_operator_and_value(condition)
                if operator in {DateOperator.IS_EMPTY, DateOperator.IS_NOT_EMPTY}:
                    # Handle 'is empty' and 'is not empty' cases
                    filters.append(self.create_date_filter(property_name, operator, value))
                else:
                    # Handle regular comparison operators (e.g., =, !=, >, <)
                    filters.append(self.create_date_filter(property_name, operator, value))

            return filters

        except ValueError as e:
            raise ValueError(f"Date parsing error for '{property_name}': {str(e)}")


    def extract_operator_and_value(self, condition: str, filter_type: FilterType) -> (Operator, Any):
        for op in operator_map.keys():
            if condition.startswith(op):
                operator = operator_map[op]
                value = condition[len(op):].strip()
                return operator, value

        operator = Operator.CONTAINS if filter_type == FilterType.MULTI_SELECT else Operator.EQUALS
        value = condition.strip()
        return operator, value

    def extract_date_operator_and_value(self, condition: str) -> (DateOperator, Any):
        """
        Extract date operator and value from the condition string.
        Supports operators like >, <, =, !=, is empty, and is not empty.
        """
        # Handle natural language expressions first
        start_date, end_date = resolve_natural_language_time(condition)
        if start_date and end_date:
            return DateOperator.ON_OR_AFTER, start_date

        # Loop through possible operators and extract the corresponding value
        for op in date_operator_map.keys():
            if condition.startswith(op):
                operator = date_operator_map[op]
                if operator in {DateOperator.IS_EMPTY, DateOperator.IS_NOT_EMPTY}:
                    # No date value needed for 'is empty' and 'is not empty'
                    return operator, True
                else:
                    # Extract the actual date value
                    date_str = condition[len(op):].strip()
                    date_val = dateparser.parse(date_str)
                    if date_val:
                        return operator, date_val.date().isoformat() if "T" not in date_str else date_val.isoformat()
        
        # If no operator is found, default to '=' for exact match
        return DateOperator.EQUALS, condition.strip()
    def create_filter(self, property_name: str, filter_type: FilterType, operator: Operator, value: Any) -> Dict[str, Any]:
        if operator in {Operator.IS_EMPTY, Operator.IS_NOT_EMPTY}:
            return {"property": property_name, filter_type.value: {operator.value: True}}
        return {"property": property_name, filter_type.value: {operator.value: value}}

    def create_date_filter(self, property_name: str, operator: DateOperator, value: Any) -> Dict[str, Any]:
        """
        Create a date filter for Notion queries.
        Handles both date comparisons and empty/not empty conditions.
        """
        if operator in {DateOperator.IS_EMPTY, DateOperator.IS_NOT_EMPTY}:
            # For 'is empty' and 'is not empty', we only need a boolean value
            return {"property": property_name, "date": {operator.value: True}}
        
        # For other operators, return the appropriate filter with the date value
        return {"property": property_name, "date": {operator.value: value}}

    def __and__(self, other: 'Condition') -> 'Condition':
        return self.combine_conditions(other, "and")

    def __or__(self, other: 'Condition') -> 'Condition':
        return self.combine_conditions(other, "or")

    def combine_conditions(self, other: 'Condition', logic: str) -> 'Condition':
        if logic == "and":
            combined_filters = {"and": self.filters + other.filters}
        elif logic == "or":
            combined_filters = {"or": [{'and': self.filters}, {'and':other.filters}]}
        else:
            raise ValueError("Logic must be 'and' or 'or'")
        new_condition = Condition(self.db_metadata)
        new_condition.filters = combined_filters
        return new_condition

    def get_filters(self) -> Dict[str, Any]:
        return {"and": self.filters} if isinstance(self.filters, list) else self.filters


# Example usage
if __name__ == "__main__":
    notion_db_metadata = {
        '날짜': {'id': 'Bmou', 'type': 'date'},
        '날짜2': {'id': 'Bmou1', 'type': 'date'},
    }

    condition = Condition(notion_db_metadata)

    user_conditions1 = {
        '날짜': '<= 2024-09-12',
    }

    user_conditions2 = {
        '날짜': '> yesterday'
    }

    pprint(condition(user_conditions1).get_filters())
    pprint(condition(user_conditions2).get_filters())

    combined_filters = condition(user_conditions1) | condition(user_conditions2)
    pprint(combined_filters.get_filters())

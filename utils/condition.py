from enum import Enum
from typing import List, Dict, Any
from datetime import datetime
import dateparser



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
    AFTER = "after"  # Compare if the date is after the given value.
    BEFORE = "before"  # Compare if the date is before the given value.
    EQUALS = "equals"  # Compare if the date is equal to the given value.
    IS_EMPTY = "is empty"  # Check if the date field is empty.
    IS_NOT_EMPTY = "is_not_empty"  # Check if the date field is not empty.
    NOT_EQUALS = "not_equals"  # Compare if the date is not equal to the given value.
    NEXT_MONTH = "next_month"  # Filter for dates within the next month.
    NEXT_WEEK = "next_week"  # Filter for dates within the next week.
    NEXT_YEAR = "next_year"  # Filter for dates within the next year.
    ON_OR_AFTER = "on_or_after"  # Compare if the date is on or after the given value.
    ON_OR_BEFORE = "on_or_before"  # Compare if the date is on or before the given value.
    PAST_MONTH = "past_month"  # Filter for dates within the past month.
    PAST_WEEK = "past_week"  # Filter for dates within the past week.
    PAST_YEAR = "past_year"  # Filter for dates within the past year.
    THIS_WEEK = "this_week"  # Filter for dates within the current week.
   

# Supported operators map
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
    "after": DateOperator.AFTER,
    "before": DateOperator.BEFORE,
    "equals": DateOperator.EQUALS,
    "is empty": DateOperator.IS_EMPTY,
    "is not empty": DateOperator.IS_NOT_EMPTY,
    "not equals": DateOperator.NOT_EQUALS,
    "next month": DateOperator.NEXT_MONTH,
    "next week": DateOperator.NEXT_WEEK,
    "next year": DateOperator.NEXT_YEAR,
    "on or after": DateOperator.ON_OR_AFTER,
    "on or before": DateOperator.ON_OR_BEFORE,
    "past month": DateOperator.PAST_MONTH,
    "past week": DateOperator.PAST_WEEK,
    "past year": DateOperator.PAST_YEAR,
    "this week": DateOperator.THIS_WEEK
}

class Condition:
    def __init__(self, db_metadata: Dict[str, Any]):
        self.db_metadata = db_metadata
        self.filters: List[Dict[str, Any]] = []

    def __call__(self, conditions: Dict[str, Any]) -> 'Condition':
        """
        Processes user-defined conditions and updates the filters.
        """
        new_condition = Condition(self.db_metadata)
        new_condition.filters = self.parse_conditions(conditions)
        return new_condition

    def parse_conditions(self, conditions: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Parses user-defined conditions based on database metadata.
        """
        filters = []
        for property_name, condition in conditions.items():
            if property_name not in self.db_metadata:
                raise ValueError(f"Property '{property_name}' not found in database metadata.")

            # Extract property metadata and filter type
            property_meta = self.db_metadata[property_name]
            filter_type = self.get_filter_type(property_meta['type'])

            # Parse condition for each property
            filters.append(self.parse_condition(property_name, filter_type, condition))

        return filters

    def get_filter_type(self, property_type: str) -> FilterType:
        """
        Maps property type to the corresponding FilterType enum.
        """
        try:
            return FilterType(property_type)
        except ValueError:
            raise ValueError(f"Unsupported property type '{property_type}'")

    def parse_condition(self, property_name: str, filter_type: FilterType, condition: str) -> Dict[str, Any]:
        """
        Parses a condition string into a filter dictionary, with support for date properties.
        """
        # For date properties, use DateOperator mapping
        if filter_type == FilterType.DATE:
            operator, value = self.extract_date_operator_and_value(condition)
            return self.create_date_filter(property_name, operator, value)
        
        # Handle other property types
        operator, value = self.extract_operator_and_value(condition, filter_type)
        return self.create_filter(property_name, filter_type, operator, value)

    def extract_operator_and_value(self, condition: str, filter_type: FilterType) -> (Operator, Any):
        """
        Extracts operator and value from a condition string.
        Defaults to "=" if no operator is found.
        """
        for op in operator_map.keys():
            if condition.startswith(op):
                operator = operator_map[op]
                value = condition[len(op):].strip()
                return operator, value

        # Default operator if none found
        operator = Operator.CONTAINS if filter_type == FilterType.MULTI_SELECT else Operator.EQUALS
        value = condition.strip()
        return operator, value

    def extract_date_operator_and_value(self, condition: str) -> (DateOperator, Any):
        """
        Extracts the date operator and value from a condition string.
        Defaults to "equals" if no operator is found. Uses 'dateparser' for flexible date inputs.
        """
        
        for op in date_operator_map.keys():
            if condition.startswith(op):                    
                operator = date_operator_map[op]
                date_str = condition[len(op):].strip()
                if date_operator_map[op] in [DateOperator.IS_EMPTY, DateOperator.IS_NOT_EMPTY,]:
                    value = True
                elif date_operator_map[op] in [DateOperator.NEXT_MONTH, DateOperator.NEXT_WEEK, DateOperator.NEXT_YEAR, DateOperator.PAST_MONTH, DateOperator.PAST_WEEK, DateOperator.PAST_YEAR, DateOperator.THIS_WEEK]:
                    value = {}
                else:
                    value = dateparser.parse(date_str, settings={'DATE_ORDER': 'YMD'}).strftime('%Y-%m-%d') if date_str else None
                return operator, value

        # Default to "equals"
        operator = DateOperator.EQUALS
        value = dateparser.parse(condition, settings={'DATE_ORDER': 'YMD'}).strftime('%Y-%m-%d')
        return operator, value

    def create_filter(self, property_name: str, filter_type: FilterType, operator: Operator, value: Any) -> Dict[str, Any]:
        """
        Builds a filter dictionary from the property name, filter type, operator, and value.
        """
        if operator in {Operator.IS_EMPTY, Operator.IS_NOT_EMPTY}:
            return {
                "property": property_name,
                filter_type.value: {operator.value: True}
            }
        return {
            "property": property_name,
            filter_type.value: {operator.value: value}
        }

    def create_date_filter(self, property_name: str, operator: DateOperator, value: Any) -> Dict[str, Any]:
        """
        Builds a filter dictionary for date properties using the operator and value.
        """
        if operator in {DateOperator.IS_EMPTY, DateOperator.IS_NOT_EMPTY}:
            return {
                "property": property_name,
                "date": {operator.value: True}
            }
        return {
            "property": property_name,
            "date": {operator.value: value}
        }

    def combine_conditions(self, other: 'Condition', logic: str) -> 'Condition':
        """
        Combines current filters with another Condition instance's filters using AND/OR logic.
        """
        if logic == "and":
            combined_filters = {"and": self.filters + other.filters}
        elif logic == "or":
            combined_filters = {"or": [self.filters, other.filters]}
        else:
            raise ValueError("Logic must be 'and' or 'or'")

        # Create a new instance with the combined filters
        new_condition = Condition(self.db_metadata)
        new_condition.filters = combined_filters
        return new_condition

    def __and__(self, other: 'Condition') -> 'Condition':
        """
        Combines filters using AND logic.
        """
        return self.combine_conditions(other, "and")

    def __or__(self, other: 'Condition') -> 'Condition':
        """
        Combines filters using OR logic.
        """
        return self.combine_conditions(other, "or")

    def get_filters(self) -> Dict[str, Any]:
        """
        Returns the constructed filters.
        """
        return {"and": self.filters} if isinstance(self.filters, list) else self.filters


# Example usage with Notion database metadata
if __name__ == "__main__":
    notion_db_metadata = {
        '날짜': {'id': 'Bmou', 'type': 'date'},
        '날짜2': {'id': 'Bmou1', 'type': 'date'},

    }

    condition = Condition(notion_db_metadata)

    user_conditions1 = {
        '날짜': 'after today',
        '날짜2': 'after today',

    }

    user_conditions2 = {
        '날짜': 'this week'
    }

    print(condition(user_conditions1).get_filters())
    print(condition(user_conditions2).get_filters())
    combined_filters = condition(user_conditions1) | condition(user_conditions2)
    print("Combined OR Filters:\n", combined_filters.get_filters())

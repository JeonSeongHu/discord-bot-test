from enum import Enum
from typing import List, Dict, Any


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
    "not_empty": Operator.IS_NOT_EMPTY
}


class Condition:
    def __init__(self, db_metadata: Dict[str, Any]):
        self.db_metadata = db_metadata
        self.filters: List[Dict[str, Any]] = []

    def __call__(self, conditions: Dict[str, Any]) -> 'Condition':
        """
        Processes user-defined conditions and updates the filters.
        """
        self.filters = self.parse_conditions(conditions)
        return self

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
        Parses a condition string into a filter dictionary.
        """
        # Extract operator from condition
        operator, value = self.extract_operator_and_value(condition, filter_type)

        # Create filter
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
        '티어 (DevRel)': {'id': 'Bmou', 'type': 'multi_select'},
        '티어 (SWE)': {'id': 'D3u%3C', 'type': 'multi_select'},
        '학번': {'id': '%7Ccl%3D', 'type': 'rich_text'},
        '활동 분야': {'id': 'prop_2', 'type': 'multi_select'},
        '희망 직군 (SWE)': {'id': '3.%3BY', 'type': 'rich_text'}
    }

    condition = Condition(notion_db_metadata)

    user_conditions1 = {
        '티어 (DevRel)': 'contains 👥 Member',
        '학번': '2021001',
        '활동 분야': 'contains 🎨 Designer',
        '희망 직군 (SWE)': '!= SWE'
    }

    user_conditions2 = {
        '티어 (DevRel)': 'contains 👥 Member',
        '학번': '2021001',
        '활동 분야': 'contains 🎨 Designer',
        '희망 직군 (SWE)': '!= SWE'
    }

    combined_filters = condition(user_conditions1) | condition(user_conditions2)
    print("Combined OR Filters:\n", combined_filters.get_filters())

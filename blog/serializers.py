from rest_framework import serializers


class CommaSeparatedListField(serializers.Field):
    def to_representation(self, value):
        if value:
            return [item.strip() for item in value.split(',')]
        return []

    def to_internal_value(self, data):
        if isinstance(data, list):
            return ', '.join(str(item).strip() for item in data)
        raise serializers.ValidationError("Expected a list of items")


class JalaliDateField(serializers.Field):
    def to_representation(self, value):
        if value:
            # Convert the Jalali date to string format
            return value.strftime('%Y-%m-%d')
        return None

    def to_internal_value(self, data):
        # Since this is a property based on an existing field,
        # we don't need to implement to_internal_value
        return data

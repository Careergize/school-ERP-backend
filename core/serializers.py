"""Serialization shared by explicit, per-model serializers."""
from rest_framework import serializers


class RecordSerializer(serializers.ModelSerializer):
    def to_internal_value(self, data):
        data = data.copy()
        for name, field in self.fields.items():
            if name in data and data[name] == '' and field.allow_null:
                data[name] = None
        return super().to_internal_value(data)

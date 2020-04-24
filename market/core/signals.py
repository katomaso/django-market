from django.dispatch import Signal

vendor_open = Signal(providing_args=["instance", "created"])
vendor_closed = Signal(providing_args=["instance", ])

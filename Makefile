trans:
	python ../manage.py makemessages -l cs
.PHONY: trans

test: unit_test model_test view_test
.PHONY: test

unit_test:
	python manage.py test tests.unit --settings=tests.unit.settings
test_unit: unit_test
.PHONY: unit_test test_unit

model_test:
	python manage.py test tests.model --settings=tests.model.settings
test_model: model_test
.PHONY: model_test test_model

view_test:
	python manage.py test tests.view --settings=tests.view.settings
test_view: view_test
.PHONY: view_test test_view

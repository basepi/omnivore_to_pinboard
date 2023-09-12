clean:
	rm -rf ./package
	rm -f ./package.zip

build: clean
	mkdir ./package
	pip install -r requirements.txt -t ./package
	cd package && zip -r ../package.zip . && cd ..
	zip package.zip omnivore_to_pinboard.py
VERSION=100

# wget -O config.js "http://api4.mapy.cz/config.js?key=&v=${VERSION}"
# wget -O smap.js "http://api4.mapy.cz/js/api/smap.js?v=${VERSION}"
# wget -O jak.js "http://api4.mapy.cz/js/api/jak.js?v=${VERSION}"


mkdir -p img/api/card/
mkdir -p img/api/compass/
mkdir -p img/api/zoom/
mkdir -p img/api/layer-switch/

for css in "poi.css" "card.css" "api.css"
do
    wget -O $css  "https://api4.mapy.cz/css/api/${css}?v${VERSION}"

    ## remove trailing slash un url-paths
    sed 's/url(\/\([^)]*\)).*/url(\1)/' <$css >"${css}m"
    mv "${css}m" $css

    ## download all images mentioned in the files
    for image in `grep "url" $css | sed 's/.*url(\([^)]*\)).*/\1/'`
    do
        wget -xO $image "http://api4.mapy.cz/${image}"
    done
done


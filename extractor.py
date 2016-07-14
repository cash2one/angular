#!/usr/bin/python
from lxml import html
from process_article import get_text, get_pic, downPic
from db.infodb import insert, save_pic, get_OneImage
import requests
import uuid
import time
import os
import sys
import re

IMG_REP_STR = "<div>&ltpicturestart--%s--pictureend&gt</div>"
PATTERN_IMG = re.compile("&ltpicturestart--(.*?)--pictureend&gt")
pub_templat = {
        "block": "//div[@class=\"msg_list_bd\"]",
        "subblock": ".//div[@class=\"sub_msg_list\"]",
        "time": ".//p[@class=\"msg_date\"]",
        "title": ".//h4[@class=\"msg_title\"]/text()",
        "link": ".//a[@class=\"sub_msg_item redirect\"]/@hrefs",
        "picture": [".//span[@class=\"thumb\"]/img/@data-src", ".//span[@class=\"thumb\"]/img/@data-src"]
        }

weixin_templat = {
        "block": "//ul[@id=\"pc_0_subd\"]",
        "subblock": ".//li",
        "time": ".//span[@class=\"sc\"]",
        "link": ".//h4/a/@href",
        "title": ".//h4/a/text()",
        "picture": ".//div[@class=\"wx-img-box\"]/a/img/@src",
        }


newsTemplate = {
        "title": "//h2/text()",
        "content": "//div[@id=\"img-content\"]",
        "pubDate": ".//em[@id=\"post-date\"]/text()",
        "remove": ".//section[@label=\"powered by 135editor.com\"]/p[position() > last() - 18]&.//div[@class=\"rich_media_tool\"]"
        }


def extract_link(dom, template):
    result = []
    blocks = dom.xpath(template["block"])
    for block in blocks:
        t = block.xpath(template['time'])
        articles = block.xpath(template['subblock'])
        for a in articles:
            title = a.xpath(template['title'])
            if title and isinstance(title, list):
                title = title[0]
            link = a.xpath(template['link'])
            if link and isinstance(link, list):
                link = link[0]
            pic_temps = template['picture']
            for t in pic_temps:
                pic = a.xpath(t)
                if pic and isinstance(pic, list):
                    pic = pic[0]
                    name = uuid.uuid4()
                    name = ''.join(str(name).split("-"))
                    pic = downPic(pic, name)
                if pic:
                    break
            #if not pic:
            #    print title
            tmp = {}
            tmp['title'] = title
            tmp['link'] = link
            tmp['thumb'] = pic
            result.append(tmp)
    return result


def down_article(link, dynamic=False):
    if dynamic:
        out = os.popen("phantomjs down.js %s" % link)
        return out.read()
    else:
        r = requests.get(link)
        if r.ok:
            return r.content
        else:
            return None


def remove_tag(dom, xpath_str):
    xpath_str = "|".join(xpath_str.split("&"))
    tag_remove = dom.xpath(xpath_str)
    for tag in tag_remove:
        parent_node = tag.getparent()
        parent_node.remove(tag)


def extract_item(dom, item, template, multi=False):
    if item not in template and not template.get(item):
        return ""
    item_value = dom.xpath(template[item])
    if multi:
        return item_value
    if item_value:
        return item_value[0]


def extract(dom, template):
    article = {}
    tag_remove = template.get("remove", "")
    article['title'] = extract_item(dom, 'title', template)
    pubDate = extract_item(dom, "pubDate", template)
    article['pubDate'] = pubDate
    content = extract_item(dom, "content", template)
    text = ""
    remove_tag(content, tag_remove)
    pics = get_pic(content)
    for p in pics:
        node = p.pop("node")
        parent_node = node.getparent()
        parent_node.replace(node, html.fromstring(IMG_REP_STR % p.get("id")))
    text += get_text(content)
    text = text.replace("<", "&lt")
    text = text.replace(">", "&gt")
    article["content"] = text
    return article


def open_file(filename):
    f = open(filename)
    content = f.read()
    f.close()
    dom = html.fromstring(content)
    return dom


def get_thumbnail(content):
    thum = PATTERN_IMG.search(content.get("content"))
    if not thum:
        return ""
    _id = thum.group(1)
    thum = get_OneImage(_id)
    if not thum:
        return ""
    return thum.get("url")


if __name__ == "__main__":
    #dom = open_file("wuhan.html")
    #r = extract_link(dom, templat)
    #print r
    history = sys.argv[1]
    out = os.popen("phantomjs down.js \"%s\"" % history)
    content = out.read()
    dom = html.fromstring(content)
    links = extract_link(dom, pub_templat)
    for link in links:
        l = link.get("link")
        thum = link.get("thumb", "")
        article = down_article(l)
        dom = html.fromstring(article)
        article_content = extract(dom, newsTemplate)
        if not thum:
            thum = get_thumbnail(article_content)
            if not thum:
                thum = ""
        _id = int(time.time() * 1000)
        article_content.update({"_id": _id, "original_url": l, "image": thum})
        insert(article_content)
    #print result.get("pubDate")
    #content = dom.xpath("//div[@id=\"img-content\"]")[0]
    #remove_tag = content.xpath(
    #        ".//p[position() > 49] | .//div[@class=\"rich_media_tool\"]")
    #remove_tag = content.xpath(".//div[@class=\"rich_media_tool\"]")
    #remove_tag(content,
    #        ".//section[@label=\"powered by 135editor.com\"]/p[position() > last() - 18]&.//div[@class=\"rich_media_tool\"]")
    #pics = get_pic(content)
    #for pic in pics:
    #    node = pic.pop("node")
    #    parent_node = node.getparent()
    #    parent_node.replace(node, html.fromstring(("<div>&lte;picturestart--%s--pictureend&gte;</div>" % pic.get("id"))))
    #print get_text(content)
    #for i in content:
    #    if i.tag == 'script':
    #        continue
    #    print i.tag

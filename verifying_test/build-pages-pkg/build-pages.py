# -*- coding: utf-8 -*-
import sys, os, glob, re, urllib, shutil, markdown

class FileParser:
    # ファイルパスをもらって、行ごとに分ける
    def __init__(self, file_path):
        if not os.path.exists(file_path):
            raise FileNotFoundError('{} does not exist'.format(file_path))
        with open(file_path) as f:
            self.lines = [line.strip() for line in f.readlines()]
            
    # タグをもらって、コンテンツの配列を出す
    def get_contents_by_tag(self, tag_name, l_pat='', r_pat=''):
        tag_name = re.escape(tag_name)
        l_pat, r_pat = re.escape(l_pat), re.escape(r_pat)

        reg1, reg2 = r'^.*' + tag_name, r'^.*' + tag_name
        if l_pat != '':
            reg1 += r'.*' + l_pat
            reg2 += r'.*' + l_pat
        reg1 += r'.*'
        reg2 += r'(.*)'
        if r_pat != '':
            reg1 += r_pat + r'.*'
            reg2 += r_pat + r'.*'
        reg1 += r'$'
        reg2 += r'$'

        matches = [line for line in self.lines if re.match(reg1, line)]
        results = [re.sub(reg2, r'\1', line).strip() for line in matches]
        return results

    def get_implicit_dependencies(self):
        reg1 = r'^#include[ ]*".*".*$'
        matches = [line for line in self.lines if re.match(reg1, line)]
        reg2 = r'^#include[ ]*"(.*)".*$'
        results = [re.sub(reg2, r'\1', line).strip() for line in matches]
        return results
        
# 現状は C++ のみのサポートを考える
class CppFile:        
    def __init__(self, file_path, source_path):
        self.file_path = os.path.normpath(file_path)
        self.source_path = source_path
        self.parser = FileParser(file_path)

        # file 指定が空なら、ファイルパスをタイトルにする
        self.title = self.parser.get_contents_by_tag(r'@file')
        if self.title == []:
            self.title = self.file_path
        else:
            # @title が複数あるなら最後を採用？？
            self.title = self.title[-1]

        self.brief = self.parser.get_contents_by_tag(r'@brief')
        self.brief.extend(self.parser.get_contents_by_tag(r'#define DESCRIPTION', r'"', r'"'))
        
        self.see = self.parser.get_contents_by_tag(r'@see')
        self.see.extend(self.parser.get_contents_by_tag(r'#define PROBLEM', r'"', r'"'))
                          
        self.docs = self.parser.get_contents_by_tag(r'@docs')
        self.docs.extend(self.parser.get_contents_by_tag(r'#define DOCS', r'"', r'"'))
        
        self.depends = self.parser.get_contents_by_tag(r'@depends')
        self.depends.extend(self.parser.get_implicit_dependencies())
        self.depends.extend(self.parser.get_contents_by_tag(r'#define REQUIRES', r'"', r'"'))
        self.depends = self.to_source_relpath(self.depends)
        
        self.required = []
        self.is_verified = self.get_verification_status()

    def get_verification_status(self):
        return False # [TODO]
        
    def to_source_relpath(self, item_list):
        result, file_dir = [], os.path.dirname(self.file_path)
        for item in item_list:
            relpath_from_source = os.path.join(file_dir, item)
            result.append(os.path.normpath(relpath_from_source))
        return result

    def set_required(self, required_list):
        self.required = required_list

class MarkdownPage:
    # requires: self.cpp_source_path, self.md_destination_path, self.destination
    def get_mark(self, cond):
        if cond:
            return ':heavy_check_mark:'
        else:
            return ':warning:'

    def get_destination(self, file_path, file_type=''):
        dst_file_dir, file_name = os.path.split(file_path)
        dst_file_dir = os.path.relpath(dst_file_dir, self.cpp_source_path)
        md_file_dir = os.path.normpath(os.path.join(self.md_destination_path, file_type, dst_file_dir))
        return os.path.join(md_file_dir, file_name)

    def get_link(self, link_href):
        return os.path.normpath(os.path.relpath(link_href, os.path.dirname(self.destination))) + '.html'

    def make_directory(self):
        dir_name, file_name = os.path.split(self.destination)
        os.makedirs(dir_name, exist_ok=True)

    def include_js(self, file_object, js_file_name):
        js_file_name = os.path.relpath(js_file_name, os.path.dirname(self.destination))
        html = '<script type="text/javascript" src="{}"></script>\n'.format(js_file_name)
        file_object.write(html)
        
    def include_css(self, file_object, css_file_name):
        css_file_name = os.path.relpath(css_file_name, os.path.dirname(self.destination))
        html = '<link rel="stylesheet" href="{}" />\n'.format(css_file_name)
        file_object.write(html)

    def convert_to_html(self):
        md_destination = self.destination + '.md'
        html_destination = self.destination + '.html'
        data = markdown.markdownFromFile(input=md_destination,
                                         output=html_destination,
                                         encoding="utf-8",
                                         extensions=['fenced_code', 'tables'])
        # with open(html_destination, 'w') as html_object:
        #     html_object.write(data)
        
class MarkdownArticle(MarkdownPage):
    def __init__(self, file_class, file_type, cpp_source_path, md_destination_path):
        self.file_class = file_class
        self.md_destination_path = md_destination_path
        self.cpp_source_path = cpp_source_path
        self.destination = self.get_destination(self.file_class.file_path, file_type)
        self.mark = self.get_mark(self.file_class.is_verified)
            
    # include (mathjax, js, css)
    def write_header(self, file_object):
        with open('./assets/site-header.txt') as f:
            file_object.write(f.read())
        self.include_js(file_object, os.path.join(self.md_destination_path, './assets/js/balloons.js'))
        self.include_js(file_object, os.path.join(self.md_destination_path, './assets/js/copy-button.js'))
        self.include_css(file_object, os.path.join(self.md_destination_path, './assets/css/copy-button.css'))
        file_object.write('\n\n')
            
    def write_title(self, file_object):
        file_object.write('# {} {}\n'.format(self.mark, self.file_class.title))
        file_object.write('\n\n')
        
    def write_contents(self, file_object, path_to_title, path_to_verification):
        back_to_top_link = os.path.relpath(os.path.join(self.md_destination_path, 'index.html'), os.path.dirname(self.destination))

        file_object.write('[Back to top page]({})\n\n'.format(back_to_top_link))

        # brief, see, docs
        for brief in self.file_class.brief:
            file_object.write('* {}\n'.format(brief))
        for see in self.file_class.see:
            file_object.write('* see: [{}]({})\n'.format(see, see))
        for docs in self.file_class.docs:
            docs = os.path.join(os.path.dirname(self.file_class.file_path), docs)
            with open(docs) as f:
                file_object.write(f.read())
        file_object.write('\n\n')

        # cpp => cpp
        self.file_class.depends = sorted(list(set(self.file_class.depends)))
        if self.file_class.depends != []:
            file_object.write('## Dependencies\n')
            for depends in self.file_class.depends:
                mark = self.get_mark(path_to_verification[depends])
                title = path_to_title[depends]
                link = self.get_link(self.get_destination(depends, 'library'))
                file_object.write('* {} [{}]({})\n'.format(mark, title, link))
            file_object.write('\n\n')
                
        # cpp <= cpp
        required_file_list = [f for f in self.file_class.required if f[-8:] != 'test.cpp']
        required_file_list = sorted(list(set(required_file_list)))
        if required_file_list != []:
            file_object.write('## Required\n')
            for required in required_file_list:
                mark = self.get_mark(path_to_verification[required])
                title = path_to_title[required]
                file_type = 'verify' if required[-8:] == 'test.cpp' else 'library'
                link = self.get_link(self.get_destination(required, file_type))
                file_object.write('* {} [{}]({})\n'.format(mark, title, link))
            file_object.write('\n\n')
                
        # cpp => test.cpp
        verified_file_list = [f for f in self.file_class.required if f[-8:] == 'test.cpp']
        verified_file_list = sorted(list(set(verified_file_list)))
        if verified_file_list != []:
            file_object.write('## Verified\n')
            for verified in verified_file_list:
                mark = self.get_mark(path_to_verification[verified])
                title = path_to_title[verified]
                link = self.get_link(self.get_destination(verified, 'verify'))
                file_object.write('* {} [{}]({})\n'.format(mark, title, link))
            file_object.write('\n\n')

        # source code
        file_object.write('## Code\n')
        file_object.write('```cpp\n')
        with open(self.file_class.file_path) as f:
            file_object.write(f.read())
        file_object.write('\n```\n\n')

        # back to top
        file_object.write('[Back to top page]({})\n\n'.format(back_to_top_link))
        
    def build(self, path_to_title, path_to_verification):
        self.make_directory()
        with open(self.destination + '.md', mode="w") as file_object:
            self.write_header(file_object)
            self.write_title(file_object)
            self.write_contents(file_object, path_to_title, path_to_verification)

class MarkdownTopPage(MarkdownPage):
    def __init__(self, cpp_source_path, md_destination_path, config):
        self.cpp_source_path = cpp_source_path
        self.md_destination_path = md_destination_path
        self.destination = os.path.join(md_destination_path, 'index')
        self.config = config

    def write_header(self, file_object):
        with open('./assets/site-header.txt') as f:
            file_object.write(f.read())
        self.include_js(file_object, os.path.join(self.md_destination_path, './assets/js/balloons.js'))
        self.include_js(file_object, os.path.join(self.md_destination_path, './assets/js/copy-button.js'))
        self.include_css(file_object, os.path.join(self.md_destination_path, './assets/css/copy-button.css'))
        file_object.write('\n\n')        
        
    def write_title(self, file_object):
        title = self.config.setdefault('title', 'C++ Competitive Programming Library')
        file_object.write('# {}\n\n'.format(title))
        description = self.config.setdefault('description', '')
        if description != '': file_object.write('{}\n\n'.format(description))
        toc = self.config.setdefault('toc', False)
        if toc:
            file_object.write('* this unordered seed list will be replaced by toc as unordered list\n')
            file_object.write('{:toc}\n\n')
        
    def write_contents(self, file_object,
                       verify_files, library_files,
                       path_to_title, path_to_verification):
        if library_files != {}:
            file_object.write('## Library\n')
            # [TODO] (フォルダごとに表示するのか、@category ごとに表示するのか)
            for library_file in library_files.keys():
                mark = self.get_mark(path_to_verification[library_file])
                title = path_to_title[library_file]
                link = self.get_link(self.get_destination(library_file, 'library'))
                file_object.write('* {} [{}]({})\n'.format(mark, title, link))
            file_object.write('\n\n')
                
        if verify_files != {}:
            file_object.write('## Verify Files\n')
            # [TODO] (library のところと同様)
            for verify_file in verify_files.keys():
                mark = self.get_mark(path_to_verification[verify_file])
                title = path_to_title[verify_file]
                link = self.get_link(self.get_destination(verify_file, 'verify'))
                file_object.write('* {} [{}]({})\n'.format(mark, title, link))
            file_object.write('\n\n')
                
    def build(self, verify_files, library_files,
              path_to_title, path_to_verification):
        self.make_directory()
        with open(self.destination + '.md', mode="w") as file_object:
            self.write_header(file_object)
            self.write_title(file_object)
            self.write_contents(file_object,
                                verify_files, library_files,
                                path_to_title, path_to_verification)
            
class PagesBuilder:
    def __init__(self, cpp_source_path, md_destination_path='./md-output', config={}, html=False):
        self.verify_files = self.get_files(cpp_source_path, r'.test.cpp')
        self.library_files = self.get_files(cpp_source_path, r'.cpp', self.verify_files)
        self.title_to_path = self.map_title2path()
        self.path_to_title = self.map_path2title()
        self.get_required()
        self.path_to_verification = self.map_path2verification()
        self.build_verify_files(cpp_source_path, md_destination_path, html)
        self.build_library_files(cpp_source_path, md_destination_path, html)
        self.build_top_page(cpp_source_path, md_destination_path, config, html)
        self.build_assets(md_destination_path)

    # ignore が付いているか？
    def is_ignored(self, file_path):
        parser = FileParser(file_path)
        ignore = parser.get_contents_by_tag(r'@ignore')        
        return ignore != []

    def get_files(self, source_path, extension, ignored_files={}):
        path = source_path + r'/**/*' + extension
        match_result = glob.glob(path, recursive=True)
        files = {}
        for matched_file in match_result:
            if not self.is_ignored(matched_file) and matched_file not in ignored_files:
                matched_file = os.path.normpath(matched_file)
                files[matched_file] = CppFile(matched_file, source_path)
        return files

    # title の重複があったらナンバリング付与
    def map_title2path(self):
        title_cnt, title_num, result = {}, {}, {}
        for cpp_class in dict(**self.library_files, **self.verify_files).values():
            title_cnt.setdefault(cpp_class.title, 0)
            title_cnt[cpp_class.title] += 1

        for cpp_class in dict(**self.library_files, **self.verify_files).values():
            title = cpp_class.title
            if title_cnt[title] >= 2:
                title_num.setdefault(title, 0);
                title_num[title] += 1
                title += '{:02}'.format(title_num[title])
            result[title] = cpp_class.file_path
        return result    
        
    def map_path2title(self):
        result = {}
        for cpp_class in dict(**self.library_files, **self.verify_files).values():
            result[cpp_class.file_path] = cpp_class.title
        return result

    def get_required(self):
        map_required = {}
        for cpp_class in dict(**self.library_files, **self.verify_files).values():
            for depends in cpp_class.depends:
                map_required.setdefault(depends, [])
                map_required[depends].append(cpp_class.file_path)

        for cpp_file in self.library_files.keys():
            map_required.setdefault(cpp_file, [])
            self.library_files[cpp_file].set_required(map_required[cpp_file])
            
        for cpp_file in self.verify_files.keys():
            map_required.setdefault(cpp_file, [])
            self.verify_files[cpp_file].set_required(map_required[cpp_file])
        
    def map_path2verification(self):
        result = {}
        # .test.cpp の verify 状況確認
        for cpp_file, cpp_class in self.verify_files.items():
            result[cpp_file] = cpp_class.is_verified

        # .cpp は、それを必要としている .test.cpp が少なくとも 1 つ存在し
        # 全ての .test.cpp が verify 済みなら OK
        for cpp_file, cpp_class in self.library_files.items():
            verify_file_cnt, cond = 0, True
            for verify in cpp_class.required:
                if verify[-8:] == 'test.cpp':
                    verify_file_cnt += 1
                    cond &= result[verify]
            result[cpp_file] = (verify_file_cnt > 0 and cond)
        return result
            
    def build_verify_files(self, cpp_source_path, md_destination_path, html_cond):
        for verify_file in self.verify_files.values():
            page = MarkdownArticle(verify_file, 'verify', cpp_source_path, md_destination_path)
            page.build(self.path_to_title, self.path_to_verification)
            if html_cond: page.convert_to_html()

    def build_library_files(self, cpp_source_path, md_destination_path, html_cond):
        for library_file in self.library_files.values():
            page = MarkdownArticle(library_file, 'library', cpp_source_path, md_destination_path)
            page.build(self.path_to_title, self.path_to_verification)
            if html_cond: page.convert_to_html()
            
    def build_top_page(self, cpp_source_path, md_destination_path, config, html_cond):
        page = MarkdownTopPage(cpp_source_path, md_destination_path, config)
        page.build(self.verify_files, self.library_files,
                   self.path_to_title, self.path_to_verification)
        if html_cond: page.convert_to_html()
        
    def build_assets(self, md_destination_path):
        destination = os.path.join(md_destination_path, './assets/')
        if os.path.exists(destination): shutil.rmtree(destination)
        shutil.copytree('./assets/', destination)
            
def main():
    config = {
        'title': 'ライブラリの HTML ビルドテスト',
        'description': 'ここに書いた内容がトップページに足されます',
        'toc': True, # default: False
    }
    builder = PagesBuilder(cpp_source_path='../../', config=config, html=True)
    
if __name__ == '__main__':
    main()

import os

from debsources.utils.conf import DebsConf, ROOT_DIR


class TestDebsConf(object):

    config = DebsConf(conf_path=os.path.join(ROOT_DIR, 'etc/config.yaml'))

    def read_section(self, section):
        return self.config.parse_section(section=section)

    def test_infra(self):
        # assert False
        infra = self.read_section("infra")
        assert infra['mirror_host'] == "ftp.de.debian.org"
        assert infra['log_file'] == '/var/log/debsources/debsources.log'

    def test_app(self):
        app = self.read_section("app")
        assert 'domain' not in app
        assert app['DOMAIN'] == 'sources.debian.net'

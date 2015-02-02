from debsources.utils.conf import DebsConf



class TestDebsConf(object):

    config = DebsConf()

    def read_section(self, section):
        return self.config.parse_section(section=section)


    def test_infra(self):
        infra = self.read_section("infra")
        assert infra['mirror_host'] == "ftp.de.debian.org"


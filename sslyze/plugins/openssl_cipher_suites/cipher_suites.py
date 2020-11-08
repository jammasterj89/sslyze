from typing import Dict, Set

from dataclasses import dataclass

from nassl.legacy_ssl_client import LegacySslClient
from nassl.ssl_client import OpenSslVersionEnum, SslClient

from sslyze.server_connectivity import TlsVersionEnum


@dataclass(frozen=True)
class CipherSuite:
    name: str
    openssl_name: str  # OpenSSL uses a different naming convention than the corresponding RFCs.
    is_anonymous: bool
    key_size: int


# Cipher suite name mappings so we can return the RFC names, instead of the OpenSSL names
# Based on https://testssl.sh/openssl-rfc.mappping.html
_SSLV2_OPENSSL_TO_RFC_NAMES_MAPPING = {
    "RC4-MD5": "SSL_CK_RC4_128_WITH_MD5",
    "EXP-RC4-MD5": "SSL_CK_RC4_128_EXPORT40_WITH_MD5",
    "RC2-CBC-MD5": "SSL_CK_RC2_128_CBC_WITH_MD5",
    "EXP-RC2-CBC-MD5": "SSL_CK_RC2_128_CBC_EXPORT40_WITH_MD5",
    "IDEA-CBC-MD5": "SSL_CK_IDEA_128_CBC_WITH_MD5",
    "DES-CBC-MD5": "SSL_CK_DES_64_CBC_WITH_MD5",
    "DES-CBC3-MD5": "SSL_CK_DES_192_EDE3_CBC_WITH_MD5",
    "RC4-64-MD5": "SSL_CK_RC4_64_WITH_MD5",
    "NULL-MD5": "TLS_RSA_WITH_NULL_MD5",
}

_TLS_OPENSSL_TO_RFC_NAMES_MAPPING = {
    "NULL-MD5": "TLS_RSA_WITH_NULL_MD5",
    "NULL-SHA": "TLS_RSA_WITH_NULL_SHA",
    "EXP-RC4-MD5": "TLS_RSA_EXPORT_WITH_RC4_40_MD5",
    "RC4-MD5": "TLS_RSA_WITH_RC4_128_MD5",
    "RC4-SHA": "TLS_RSA_WITH_RC4_128_SHA",
    "EXP-RC2-CBC-MD5": "TLS_RSA_EXPORT_WITH_RC2_CBC_40_MD5",
    "IDEA-CBC-SHA": "TLS_RSA_WITH_IDEA_CBC_SHA",
    "EXP-DES-CBC-SHA": "TLS_RSA_EXPORT_WITH_DES40_CBC_SHA",
    "DES-CBC-SHA": "TLS_RSA_WITH_DES_CBC_SHA",
    "DES-CBC3-SHA": "TLS_RSA_WITH_3DES_EDE_CBC_SHA",
    "EXP-DH-DSS-DES-CBC-SHA": "TLS_DH_DSS_EXPORT_WITH_DES40_CBC_SHA",
    "DH-DSS-DES-CBC-SHA": "TLS_DH_DSS_WITH_DES_CBC_SHA",
    "DH-DSS-DES-CBC3-SHA": "TLS_DH_DSS_WITH_3DES_EDE_CBC_SHA",
    "EXP-DH-RSA-DES-CBC-SHA": "TLS_DH_RSA_EXPORT_WITH_DES40_CBC_SHA",
    "DH-RSA-DES-CBC-SHA": "TLS_DH_RSA_WITH_DES_CBC_SHA",
    "DH-RSA-DES-CBC3-SHA": "TLS_DH_RSA_WITH_3DES_EDE_CBC_SHA",
    "EXP-EDH-DSS-DES-CBC-SHA": "TLS_DHE_DSS_EXPORT_WITH_DES40_CBC_SHA",
    "EDH-DSS-DES-CBC-SHA": "TLS_DHE_DSS_WITH_DES_CBC_SHA",
    "EDH-DSS-DES-CBC3-SHA": "TLS_DHE_DSS_WITH_3DES_EDE_CBC_SHA",
    "EXP-EDH-RSA-DES-CBC-SHA": "TLS_DHE_RSA_EXPORT_WITH_DES40_CBC_SHA",
    "EDH-RSA-DES-CBC-SHA": "TLS_DHE_RSA_WITH_DES_CBC_SHA",
    "EDH-RSA-DES-CBC3-SHA": "TLS_DHE_RSA_WITH_3DES_EDE_CBC_SHA",
    "EXP-ADH-RC4-MD5": "TLS_DH_anon_EXPORT_WITH_RC4_40_MD5",
    "ADH-RC4-MD5": "TLS_DH_anon_WITH_RC4_128_MD5",
    "EXP-ADH-DES-CBC-SHA": "TLS_DH_anon_EXPORT_WITH_DES40_CBC_SHA",
    "ADH-DES-CBC-SHA": "TLS_DH_anon_WITH_DES_CBC_SHA",
    "ADH-DES-CBC3-SHA": "TLS_DH_anon_WITH_3DES_EDE_CBC_SHA",
    "KRB5-DES-CBC-SHA": "TLS_KRB5_WITH_DES_CBC_SHA",
    "KRB5-DES-CBC3-SHA": "TLS_KRB5_WITH_3DES_EDE_CBC_SHA",
    "KRB5-RC4-SHA": "TLS_KRB5_WITH_RC4_128_SHA",
    "KRB5-IDEA-CBC-SHA": "TLS_KRB5_WITH_IDEA_CBC_SHA",
    "KRB5-DES-CBC-MD5": "TLS_KRB5_WITH_DES_CBC_MD5",
    "KRB5-DES-CBC3-MD5": "TLS_KRB5_WITH_3DES_EDE_CBC_MD5",
    "KRB5-RC4-MD5": "TLS_KRB5_WITH_RC4_128_MD5",
    "KRB5-IDEA-CBC-MD5": "TLS_KRB5_WITH_IDEA_CBC_MD5",
    "EXP-KRB5-DES-CBC-SHA": "TLS_KRB5_EXPORT_WITH_DES_CBC_40_SHA",
    "EXP-KRB5-RC2-CBC-SHA": "TLS_KRB5_EXPORT_WITH_RC2_CBC_40_SHA",
    "EXP-KRB5-RC4-SHA": "TLS_KRB5_EXPORT_WITH_RC4_40_SHA",
    "EXP-KRB5-DES-CBC-MD5": "TLS_KRB5_EXPORT_WITH_DES_CBC_40_MD5",
    "EXP-KRB5-RC2-CBC-MD5": "TLS_KRB5_EXPORT_WITH_RC2_CBC_40_MD5",
    "EXP-KRB5-RC4-MD5": "TLS_KRB5_EXPORT_WITH_RC4_40_MD5",
    "AES128-SHA": "TLS_RSA_WITH_AES_128_CBC_SHA",
    "DH-DSS-AES128-SHA": "TLS_DH_DSS_WITH_AES_128_CBC_SHA",
    "DH-RSA-AES128-SHA": "TLS_DH_RSA_WITH_AES_128_CBC_SHA",
    "DHE-DSS-AES128-SHA": "TLS_DHE_DSS_WITH_AES_128_CBC_SHA",
    "DHE-RSA-AES128-SHA": "TLS_DHE_RSA_WITH_AES_128_CBC_SHA",
    "ADH-AES128-SHA": "TLS_DH_anon_WITH_AES_128_CBC_SHA",
    "AES256-SHA": "TLS_RSA_WITH_AES_256_CBC_SHA",
    "DH-DSS-AES256-SHA": "TLS_DH_DSS_WITH_AES_256_CBC_SHA",
    "DH-RSA-AES256-SHA": "TLS_DH_RSA_WITH_AES_256_CBC_SHA",
    "DHE-DSS-AES256-SHA": "TLS_DHE_DSS_WITH_AES_256_CBC_SHA",
    "DHE-RSA-AES256-SHA": "TLS_DHE_RSA_WITH_AES_256_CBC_SHA",
    "ADH-AES256-SHA": "TLS_DH_anon_WITH_AES_256_CBC_SHA",
    "NULL-SHA256": "TLS_RSA_WITH_NULL_SHA256",
    "AES128-SHA256": "TLS_RSA_WITH_AES_128_CBC_SHA256",
    "AES256-SHA256": "TLS_RSA_WITH_AES_256_CBC_SHA256",
    "DH-DSS-AES128-SHA256": "TLS_DH_DSS_WITH_AES_128_CBC_SHA256",
    "DH-RSA-AES128-SHA256": "TLS_DH_RSA_WITH_AES_128_CBC_SHA256",
    "DHE-DSS-AES128-SHA256": "TLS_DHE_DSS_WITH_AES_128_CBC_SHA256",
    "CAMELLIA128-SHA": "TLS_RSA_WITH_CAMELLIA_128_CBC_SHA",
    "DH-DSS-CAMELLIA128-SHA": "TLS_DH_DSS_WITH_CAMELLIA_128_CBC_SHA",
    "DH-RSA-CAMELLIA128-SHA": "TLS_DH_RSA_WITH_CAMELLIA_128_CBC_SHA",
    "DHE-DSS-CAMELLIA128-SHA": "TLS_DHE_DSS_WITH_CAMELLIA_128_CBC_SHA",
    "DHE-RSA-CAMELLIA128-SHA": "TLS_DHE_RSA_WITH_CAMELLIA_128_CBC_SHA",
    "ADH-CAMELLIA128-SHA": "TLS_DH_anon_WITH_CAMELLIA_128_CBC_SHA",
    "EXP1024-DES-CBC-SHA": "TLS_RSA_EXPORT1024_WITH_DES_CBC_SHA",
    "EXP1024-DHE-DSS-DES-CBC-SHA": "TLS_DHE_DSS_EXPORT1024_WITH_DES_CBC_SHA",
    "EXP1024-RC4-SHA": "TLS_RSA_EXPORT1024_WITH_RC4_56_SHA",
    "EXP1024-RC4-MD5": "TLS_RSA_EXPORT1024_WITH_RC4_56_MD5",
    "EXP1024-RC2-CBC-MD5": "TLS_RSA_EXPORT1024_WITH_RC2_CBC_56_MD5",
    "EXP1024-DHE-DSS-RC4-SHA": "TLS_DHE_DSS_EXPORT1024_WITH_RC4_56_SHA",
    "DHE-DSS-RC4-SHA": "TLS_DHE_DSS_WITH_RC4_128_SHA",
    "DHE-RSA-AES128-SHA256": "TLS_DHE_RSA_WITH_AES_128_CBC_SHA256",
    "DH-DSS-AES256-SHA256": "TLS_DH_DSS_WITH_AES_256_CBC_SHA256",
    "DH-RSA-AES256-SHA256": "TLS_DH_RSA_WITH_AES_256_CBC_SHA256",
    "DHE-DSS-AES256-SHA256": "TLS_DHE_DSS_WITH_AES_256_CBC_SHA256",
    "DHE-RSA-AES256-SHA256": "TLS_DHE_RSA_WITH_AES_256_CBC_SHA256",
    "ADH-AES128-SHA256": "TLS_DH_anon_WITH_AES_128_CBC_SHA256",
    "ADH-AES256-SHA256": "TLS_DH_anon_WITH_AES_256_CBC_SHA256",
    "GOST94-GOST89-GOST89": "TLS_GOSTR341094_WITH_28147_CNT_IMIT",
    "GOST2001-GOST89-GOST89": "TLS_GOSTR341001_WITH_28147_CNT_IMIT",
    "CAMELLIA256-SHA": "TLS_RSA_WITH_CAMELLIA_256_CBC_SHA",
    "DH-DSS-CAMELLIA256-SHA": "TLS_DH_DSS_WITH_CAMELLIA_256_CBC_SHA",
    "DH-RSA-CAMELLIA256-SHA": "TLS_DH_RSA_WITH_CAMELLIA_256_CBC_SHA",
    "DHE-DSS-CAMELLIA256-SHA": "TLS_DHE_DSS_WITH_CAMELLIA_256_CBC_SHA",
    "DHE-RSA-CAMELLIA256-SHA": "TLS_DHE_RSA_WITH_CAMELLIA_256_CBC_SHA",
    "ADH-CAMELLIA256-SHA": "TLS_DH_anon_WITH_CAMELLIA_256_CBC_SHA",
    "PSK-RC4-SHA": "TLS_PSK_WITH_RC4_128_SHA",
    "PSK-3DES-EDE-CBC-SHA": "TLS_PSK_WITH_3DES_EDE_CBC_SHA",
    "PSK-AES128-CBC-SHA": "TLS_PSK_WITH_AES_128_CBC_SHA",
    "PSK-AES256-CBC-SHA": "TLS_PSK_WITH_AES_256_CBC_SHA",
    "RSA-PSK-RC4-SHA": "TLS_RSA_PSK_WITH_RC4_128_SHA",
    "RSA-PSK-3DES-EDE-CBC-SHA": "TLS_RSA_PSK_WITH_3DES_EDE_CBC_SHA",
    "RSA-PSK-AES128-CBC-SHA": "TLS_RSA_PSK_WITH_AES_128_CBC_SHA",
    "RSA-PSK-AES256-CBC-SHA": "TLS_RSA_PSK_WITH_AES_256_CBC_SHA",
    "SEED-SHA": "TLS_RSA_WITH_SEED_CBC_SHA",
    "DH-DSS-SEED-SHA": "TLS_DH_DSS_WITH_SEED_CBC_SHA",
    "DH-RSA-SEED-SHA": "TLS_DH_RSA_WITH_SEED_CBC_SHA",
    "DHE-DSS-SEED-SHA": "TLS_DHE_DSS_WITH_SEED_CBC_SHA",
    "DHE-RSA-SEED-SHA": "TLS_DHE_RSA_WITH_SEED_CBC_SHA",
    "ADH-SEED-SHA": "TLS_DH_anon_WITH_SEED_CBC_SHA",
    "AES128-GCM-SHA256": "TLS_RSA_WITH_AES_128_GCM_SHA256",
    "AES256-GCM-SHA384": "TLS_RSA_WITH_AES_256_GCM_SHA384",
    "DHE-RSA-AES128-GCM-SHA256": "TLS_DHE_RSA_WITH_AES_128_GCM_SHA256",
    "DHE-RSA-AES256-GCM-SHA384": "TLS_DHE_RSA_WITH_AES_256_GCM_SHA384",
    "DH-RSA-AES128-GCM-SHA256": "TLS_DH_RSA_WITH_AES_128_GCM_SHA256",
    "DH-RSA-AES256-GCM-SHA384": "TLS_DH_RSA_WITH_AES_256_GCM_SHA384",
    "DHE-DSS-AES128-GCM-SHA256": "TLS_DHE_DSS_WITH_AES_128_GCM_SHA256",
    "DHE-DSS-AES256-GCM-SHA384": "TLS_DHE_DSS_WITH_AES_256_GCM_SHA384",
    "DH-DSS-AES128-GCM-SHA256": "TLS_DH_DSS_WITH_AES_128_GCM_SHA256",
    "DH-DSS-AES256-GCM-SHA384": "TLS_DH_DSS_WITH_AES_256_GCM_SHA384",
    "ADH-AES128-GCM-SHA256": "TLS_DH_anon_WITH_AES_128_GCM_SHA256",
    "ADH-AES256-GCM-SHA384": "TLS_DH_anon_WITH_AES_256_GCM_SHA384",
    "CAMELLIA128-SHA256": "TLS_RSA_WITH_CAMELLIA_128_CBC_SHA256",
    "DH-DSS-CAMELLIA128-SHA256": "TLS_DH_DSS_WITH_CAMELLIA_128_CBC_SHA256",
    "DH-RSA-CAMELLIA128-SHA256": "TLS_DH_RSA_WITH_CAMELLIA_128_CBC_SHA256",
    "DHE-DSS-CAMELLIA128-SHA256": "TLS_DHE_DSS_WITH_CAMELLIA_128_CBC_SHA256",
    "DHE-RSA-CAMELLIA128-SHA256": "TLS_DHE_RSA_WITH_CAMELLIA_128_CBC_SHA256",
    "ADH-CAMELLIA128-SHA256": "TLS_DH_anon_WITH_CAMELLIA_128_CBC_SHA256",
    "CAMELLIA256-SHA256": "TLS_RSA_WITH_CAMELLIA_256_CBC_SHA256",
    "DH-DSS-CAMELLIA256-SHA256": "TLS_DH_DSS_WITH_CAMELLIA_256_CBC_SHA256",
    "DH-RSA-CAMELLIA256-SHA256": "TLS_DH_RSA_WITH_CAMELLIA_256_CBC_SHA256",
    "DHE-DSS-CAMELLIA256-SHA256": "TLS_DHE_DSS_WITH_CAMELLIA_256_CBC_SHA256",
    "DHE-RSA-CAMELLIA256-SHA256": "TLS_DHE_RSA_WITH_CAMELLIA_256_CBC_SHA256",
    "ADH-CAMELLIA256-SHA256": "TLS_DH_anon_WITH_CAMELLIA_256_CBC_SHA256",
    "TLS_FALLBACK_SCSV": "TLS_FALLBACK_SCSV",
    "ECDH-ECDSA-NULL-SHA": "TLS_ECDH_ECDSA_WITH_NULL_SHA",
    "ECDH-ECDSA-RC4-SHA": "TLS_ECDH_ECDSA_WITH_RC4_128_SHA",
    "ECDH-ECDSA-DES-CBC3-SHA": "TLS_ECDH_ECDSA_WITH_3DES_EDE_CBC_SHA",
    "ECDH-ECDSA-AES128-SHA": "TLS_ECDH_ECDSA_WITH_AES_128_CBC_SHA",
    "ECDH-ECDSA-AES256-SHA": "TLS_ECDH_ECDSA_WITH_AES_256_CBC_SHA",
    "ECDHE-ECDSA-NULL-SHA": "TLS_ECDHE_ECDSA_WITH_NULL_SHA",
    "ECDHE-ECDSA-RC4-SHA": "TLS_ECDHE_ECDSA_WITH_RC4_128_SHA",
    "ECDHE-ECDSA-DES-CBC3-SHA": "TLS_ECDHE_ECDSA_WITH_3DES_EDE_CBC_SHA",
    "ECDHE-ECDSA-AES128-SHA": "TLS_ECDHE_ECDSA_WITH_AES_128_CBC_SHA",
    "ECDHE-ECDSA-AES256-SHA": "TLS_ECDHE_ECDSA_WITH_AES_256_CBC_SHA",
    "ECDH-RSA-NULL-SHA": "TLS_ECDH_RSA_WITH_NULL_SHA",
    "ECDH-RSA-RC4-SHA": "TLS_ECDH_RSA_WITH_RC4_128_SHA",
    "ECDH-RSA-DES-CBC3-SHA": "TLS_ECDH_RSA_WITH_3DES_EDE_CBC_SHA",
    "ECDH-RSA-AES128-SHA": "TLS_ECDH_RSA_WITH_AES_128_CBC_SHA",
    "ECDH-RSA-AES256-SHA": "TLS_ECDH_RSA_WITH_AES_256_CBC_SHA",
    "ECDHE-RSA-NULL-SHA": "TLS_ECDHE_RSA_WITH_NULL_SHA",
    "ECDHE-RSA-RC4-SHA": "TLS_ECDHE_RSA_WITH_RC4_128_SHA",
    "ECDHE-RSA-DES-CBC3-SHA": "TLS_ECDHE_RSA_WITH_3DES_EDE_CBC_SHA",
    "ECDHE-RSA-AES128-SHA": "TLS_ECDHE_RSA_WITH_AES_128_CBC_SHA",
    "ECDHE-RSA-AES256-SHA": "TLS_ECDHE_RSA_WITH_AES_256_CBC_SHA",
    "AECDH-NULL-SHA": "TLS_ECDH_anon_WITH_NULL_SHA",
    "AECDH-RC4-SHA": "TLS_ECDH_anon_WITH_RC4_128_SHA",
    "AECDH-DES-CBC3-SHA": "TLS_ECDH_anon_WITH_3DES_EDE_CBC_SHA",
    "AECDH-AES128-SHA": "TLS_ECDH_anon_WITH_AES_128_CBC_SHA",
    "AECDH-AES256-SHA": "TLS_ECDH_anon_WITH_AES_256_CBC_SHA",
    "SRP-3DES-EDE-CBC-SHA": "TLS_SRP_SHA_WITH_3DES_EDE_CBC_SHA",
    "SRP-RSA-3DES-EDE-CBC-SHA": "TLS_SRP_SHA_RSA_WITH_3DES_EDE_CBC_SHA",
    "SRP-DSS-3DES-EDE-CBC-SHA": "TLS_SRP_SHA_DSS_WITH_3DES_EDE_CBC_SHA",
    "SRP-AES-128-CBC-SHA": "TLS_SRP_SHA_WITH_AES_128_CBC_SHA",
    "SRP-RSA-AES-128-CBC-SHA": "TLS_SRP_SHA_RSA_WITH_AES_128_CBC_SHA",
    "SRP-DSS-AES-128-CBC-SHA": "TLS_SRP_SHA_DSS_WITH_AES_128_CBC_SHA",
    "SRP-AES-256-CBC-SHA": "TLS_SRP_SHA_WITH_AES_256_CBC_SHA",
    "SRP-RSA-AES-256-CBC-SHA": "TLS_SRP_SHA_RSA_WITH_AES_256_CBC_SHA",
    "SRP-DSS-AES-256-CBC-SHA": "TLS_SRP_SHA_DSS_WITH_AES_256_CBC_SHA",
    "ECDHE-ECDSA-AES128-SHA256": "TLS_ECDHE_ECDSA_WITH_AES_128_CBC_SHA256",
    "ECDHE-ECDSA-AES256-SHA384": "TLS_ECDHE_ECDSA_WITH_AES_256_CBC_SHA384",
    "ECDH-ECDSA-AES128-SHA256": "TLS_ECDH_ECDSA_WITH_AES_128_CBC_SHA256",
    "ECDH-ECDSA-AES256-SHA384": "TLS_ECDH_ECDSA_WITH_AES_256_CBC_SHA384",
    "ECDHE-RSA-AES128-SHA256": "TLS_ECDHE_RSA_WITH_AES_128_CBC_SHA256",
    "ECDHE-RSA-AES256-SHA384": "TLS_ECDHE_RSA_WITH_AES_256_CBC_SHA384",
    "ECDH-RSA-AES128-SHA256": "TLS_ECDH_RSA_WITH_AES_128_CBC_SHA256",
    "ECDH-RSA-AES256-SHA384": "TLS_ECDH_RSA_WITH_AES_256_CBC_SHA384",
    "ECDHE-ECDSA-AES128-GCM-SHA256": "TLS_ECDHE_ECDSA_WITH_AES_128_GCM_SHA256",
    "ECDHE-ECDSA-AES256-GCM-SHA384": "TLS_ECDHE_ECDSA_WITH_AES_256_GCM_SHA384",
    "ECDH-ECDSA-AES128-GCM-SHA256": "TLS_ECDH_ECDSA_WITH_AES_128_GCM_SHA256",
    "ECDH-ECDSA-AES256-GCM-SHA384": "TLS_ECDH_ECDSA_WITH_AES_256_GCM_SHA384",
    "ECDHE-RSA-AES128-GCM-SHA256": "TLS_ECDHE_RSA_WITH_AES_128_GCM_SHA256",
    "ECDHE-RSA-AES256-GCM-SHA384": "TLS_ECDHE_RSA_WITH_AES_256_GCM_SHA384",
    "ECDH-RSA-AES128-GCM-SHA256": "TLS_ECDH_RSA_WITH_AES_128_GCM_SHA256",
    "ECDH-RSA-AES256-GCM-SHA384": "TLS_ECDH_RSA_WITH_AES_256_GCM_SHA384",
    "ECDHE-ECDSA-CAMELLIA128-SHA256": "TLS_ECDHE_ECDSA_WITH_CAMELLIA_128_CBC_SHA256",
    "ECDHE-ECDSA-CAMELLIA256-SHA384": "TLS_ECDHE_ECDSA_WITH_CAMELLIA_256_CBC_SHA384",
    "ECDH-ECDSA-CAMELLIA128-SHA256": "TLS_ECDH_ECDSA_WITH_CAMELLIA_128_CBC_SHA256",
    "ECDH-ECDSA-CAMELLIA256-SHA384": "TLS_ECDH_ECDSA_WITH_CAMELLIA_256_CBC_SHA384",
    "ECDHE-RSA-CAMELLIA128-SHA256": "TLS_ECDHE_RSA_WITH_CAMELLIA_128_CBC_SHA256",
    "ECDHE-RSA-CAMELLIA256-SHA384": "TLS_ECDHE_RSA_WITH_CAMELLIA_256_CBC_SHA384",
    "ECDH-RSA-CAMELLIA128-SHA256": "TLS_ECDH_RSA_WITH_CAMELLIA_128_CBC_SHA256",
    "ECDH-RSA-CAMELLIA256-SHA384": "TLS_ECDH_RSA_WITH_CAMELLIA_256_CBC_SHA384",
    "ECDHE-RSA-CHACHA20-POLY1305": "TLS_ECDHE_RSA_WITH_CHACHA20_POLY1305_SHA256",
    "ECDHE-ECDSA-CHACHA20-POLY1305": "TLS_ECDHE_ECDSA_WITH_CHACHA20_POLY1305_SHA256",
    "DHE-RSA-CHACHA20-POLY1305": "TLS_DHE_RSA_WITH_CHACHA20_POLY1305_SHA256",
    "ECDHE-RSA-CHACHA20-POLY1305-OLD": "OLD_TLS_ECDHE_RSA_WITH_CHACHA20_POLY1305_SHA256",
    "ECDHE-ECDSA-CHACHA20-POLY1305-OLD": "OLD_TLS_ECDHE_ECDSA_WITH_CHACHA20_POLY1305_SHA256",
    "DHE-RSA-CHACHA20-POLY1305-OLD": "OLD_TLS_DHE_RSA_WITH_CHACHA20_POLY1305_SHA256",
    "DHE-RSA-DES-CBC3-SHA": "TLS_DHE_RSA_WITH_3DES_EDE_CBC_SHA",
    "DHE-DSS-DES-CBC3-SHA": "TLS_DHE_DSS_WITH_3DES_EDE_CBC_SHA",
    "AES128-CCM": "TLS_RSA_WITH_AES_128_CCM",
    "AES256-CCM": "TLS_RSA_WITH_AES_256_CCM",
    "DHE-RSA-AES128-CCM": "TLS_DHE_RSA_WITH_AES_128_CCM",
    "DHE-RSA-AES256-CCM": "TLS_DHE_RSA_WITH_AES_256_CCM",
    "AES128-CCM8": "TLS_RSA_WITH_AES_128_CCM_8",
    "AES256-CCM8": "TLS_RSA_WITH_AES_256_CCM_8",
    "DHE-RSA-AES128-CCM8": "TLS_DHE_RSA_WITH_AES_128_CCM_8",
    "DHE-RSA-AES256-CCM8": "TLS_DHE_RSA_WITH_AES_256_CCM_8",
    "ECDHE-ECDSA-AES128-CCM": "TLS_ECDHE_ECDSA_WITH_AES_128_CCM",
    "ECDHE-ECDSA-AES256-CCM": "TLS_ECDHE_ECDSA_WITH_AES_256_CCM",
    "ECDHE-ECDSA-AES128-CCM8": "TLS_ECDHE_ECDSA_WITH_AES_128_CCM_8",
    "ECDHE-ECDSA-AES256-CCM8": "TLS_ECDHE_ECDSA_WITH_AES_256_CCM_8",
    "ARIA128-GCM-SHA256": "TLS_RSA_WITH_ARIA_128_GCM_SHA256",
    "ARIA256-GCM-SHA384": "TLS_RSA_WITH_ARIA_256_GCM_SHA384",
    "DHE-DSS-ARIA128-GCM-SHA256": "TLS_DHE_DSS_WITH_ARIA_128_GCM_SHA256",
    "DHE-DSS-ARIA256-GCM-SHA384": "TLS_DHE_DSS_WITH_ARIA_256_GCM_SHA384",
    "DHE-PSK-3DES-EDE-CBC-SHA": "TLS_DHE_PSK_WITH_3DES_EDE_CBC_SHA",
    "DHE-PSK-AES128-CBC-SHA": "TLS_DHE_PSK_WITH_AES_128_CBC_SHA",
    "DHE-PSK-AES128-CBC-SHA256": "TLS_DHE_PSK_WITH_AES_128_CBC_SHA256",
    "DHE-PSK-AES128-CCM": "TLS_DHE_PSK_WITH_AES_128_CCM",
    "DHE-PSK-AES128-CCM8": "TLS_PSK_DHE_WITH_AES_128_CCM_8",
    "DHE-PSK-AES128-GCM-SHA256": "TLS_DHE_PSK_WITH_AES_128_GCM_SHA256",
    "DHE-PSK-AES256-CBC-SHA": "TLS_DHE_PSK_WITH_AES_256_CBC_SHA",
    "DHE-PSK-AES256-CBC-SHA384": "TLS_DHE_PSK_WITH_AES_256_CBC_SHA384",
    "DHE-PSK-AES256-CCM": "TLS_DHE_PSK_WITH_AES_256_CCM",
    "DHE-PSK-AES256-CCM8": "TLS_PSK_DHE_WITH_AES_256_CCM_8",
    "DHE-PSK-AES256-GCM-SHA384": "TLS_DHE_PSK_WITH_AES_256_GCM_SHA384",
    "DHE-PSK-ARIA128-GCM-SHA256": "TLS_DHE_PSK_WITH_ARIA_128_GCM_SHA256",
    "DHE-PSK-ARIA256-GCM-SHA384": "TLS_DHE_PSK_WITH_ARIA_256_GCM_SHA384",
    "DHE-PSK-CAMELLIA128-SHA256": "TLS_DHE_PSK_WITH_CAMELLIA_128_CBC_SHA256",
    "DHE-PSK-CAMELLIA256-SHA384": "TLS_DHE_PSK_WITH_CAMELLIA_256_CBC_SHA384",
    "DHE-PSK-CHACHA20-POLY1305": "TLS_DHE_PSK_WITH_CHACHA20_POLY1305_SHA256",
    "DHE-PSK-NULL-SHA": "TLS_DHE_PSK_WITH_NULL_SHA",
    "DHE-PSK-NULL-SHA256": "TLS_DHE_PSK_WITH_NULL_SHA256",
    "DHE-PSK-NULL-SHA384": "TLS_DHE_PSK_WITH_NULL_SHA384",
    "DHE-PSK-RC4-SHA": "TLS_DHE_PSK_WITH_RC4_128_SHA",
    "DHE-RSA-ARIA128-GCM-SHA256": "TLS_DHE_RSA_WITH_ARIA_128_GCM_SHA256",
    "DHE-RSA-ARIA256-GCM-SHA384": "TLS_DHE_RSA_WITH_ARIA_256_GCM_SHA384",
    "ECDHE-ARIA128-GCM-SHA256": "TLS_ECDHE_RSA_WITH_ARIA_128_GCM_SHA256",
    "ECDHE-ARIA256-GCM-SHA384": "TLS_ECDHE_RSA_WITH_ARIA_256_GCM_SHA384",
    "ECDHE-ECDSA-ARIA128-GCM-SHA256": "TLS_ECDHE_ECDSA_WITH_ARIA_128_GCM_SHA256",
    "ECDHE-ECDSA-ARIA256-GCM-SHA384": "TLS_ECDHE_ECDSA_WITH_ARIA_256_GCM_SHA384",
    "ECDHE-PSK-3DES-EDE-CBC-SHA": "TLS_ECDHE_PSK_WITH_3DES_EDE_CBC_SHA",
    "ECDHE-PSK-AES128-CBC-SHA": "TLS_ECDHE_PSK_WITH_AES_128_CBC_SHA",
    "ECDHE-PSK-AES128-CBC-SHA256": "TLS_ECDHE_PSK_WITH_AES_128_CBC_SHA256",
    "ECDHE-PSK-AES256-CBC-SHA": "TLS_ECDHE_PSK_WITH_AES_256_CBC_SHA",
    "ECDHE-PSK-AES256-CBC-SHA384": "TLS_ECDHE_PSK_WITH_AES_256_CBC_SHA384",
    "ECDHE-PSK-CAMELLIA128-SHA256": "TLS_ECDHE_PSK_WITH_CAMELLIA_128_CBC_SHA256",
    "ECDHE-PSK-CAMELLIA256-SHA384": "TLS_ECDHE_PSK_WITH_CAMELLIA_256_CBC_SHA384",
    "ECDHE-PSK-CHACHA20-POLY1305": "TLS_ECDHE_PSK_WITH_CHACHA20_POLY1305_SHA256",
    "ECDHE-PSK-NULL-SHA": "TLS_ECDHE_PSK_WITH_NULL_SHA",
    "ECDHE-PSK-NULL-SHA256": "TLS_ECDHE_PSK_WITH_NULL_SHA256",
    "ECDHE-PSK-NULL-SHA384": "TLS_ECDHE_PSK_WITH_NULL_SHA384",
    "ECDHE-PSK-RC4-SHA": "TLS_ECDHE_PSK_WITH_RC4_128_SHA",
    "GOST2001-NULL-GOST94": "TLS_GOSTR341001_WITH_NULL_GOSTR3411",
    "GOST94-NULL-GOST94": "TLS_GOSTR341094_WITH_NULL_GOSTR3411",
    "PSK-AES128-CBC-SHA256": "TLS_PSK_WITH_AES_128_CBC_SHA256",
    "PSK-AES128-CCM": "TLS_PSK_WITH_AES_128_CCM",
    "PSK-AES128-CCM8": "TLS_PSK_WITH_AES_128_CCM_8",
    "PSK-AES128-GCM-SHA256": "TLS_PSK_WITH_AES_128_GCM_SHA256",
    "PSK-AES256-CBC-SHA384": "TLS_PSK_WITH_AES_256_CBC_SHA384",
    "PSK-AES256-CCM": "TLS_PSK_WITH_AES_256_CCM",
    "PSK-AES256-CCM8": "TLS_PSK_WITH_AES_256_CCM_8",
    "PSK-AES256-GCM-SHA384": "TLS_PSK_WITH_AES_256_GCM_SHA384",
    "PSK-ARIA128-GCM-SHA256": "TLS_PSK_WITH_ARIA_128_GCM_SHA256",
    "PSK-ARIA256-GCM-SHA384": "TLS_PSK_WITH_ARIA_256_GCM_SHA384",
    "PSK-CAMELLIA128-SHA256": "TLS_PSK_WITH_CAMELLIA_128_CBC_SHA256",
    "PSK-CAMELLIA256-SHA384": "TLS_PSK_WITH_CAMELLIA_256_CBC_SHA384",
    "PSK-CHACHA20-POLY1305": "TLS_PSK_WITH_CHACHA20_POLY1305_SHA256",
    "PSK-NULL-SHA": "TLS_PSK_WITH_NULL_SHA",
    "PSK-NULL-SHA256": "TLS_PSK_WITH_NULL_SHA256",
    "PSK-NULL-SHA384": "TLS_PSK_WITH_NULL_SHA384",
    "RSA-PSK-AES128-CBC-SHA256": "TLS_RSA_PSK_WITH_AES_128_CBC_SHA256",
    "RSA-PSK-AES128-GCM-SHA256": "TLS_RSA_PSK_WITH_AES_128_GCM_SHA256",
    "RSA-PSK-AES256-CBC-SHA384": "TLS_RSA_PSK_WITH_AES_256_CBC_SHA384",
    "RSA-PSK-AES256-GCM-SHA384": "TLS_RSA_PSK_WITH_AES_256_GCM_SHA384",
    "RSA-PSK-ARIA128-GCM-SHA256": "TLS_RSA_PSK_WITH_ARIA_128_GCM_SHA256",
    "RSA-PSK-ARIA256-GCM-SHA384": "TLS_RSA_PSK_WITH_ARIA_256_GCM_SHA384",
    "RSA-PSK-CAMELLIA128-SHA256": "TLS_RSA_PSK_WITH_CAMELLIA_128_CBC_SHA256",
    "RSA-PSK-CAMELLIA256-SHA384": "TLS_RSA_PSK_WITH_CAMELLIA_256_CBC_SHA384",
    "RSA-PSK-CHACHA20-POLY1305": "TLS_RSA_PSK_WITH_CHACHA20_POLY1305_SHA256",
    "RSA-PSK-NULL-SHA": "TLS_RSA_PSK_WITH_NULL_SHA",
    "RSA-PSK-NULL-SHA256": "TLS_RSA_PSK_WITH_NULL_SHA256",
    "RSA-PSK-NULL-SHA384": "TLS_RSA_PSK_WITH_NULL_SHA384",
}


_OPENSSL_TO_RFC_NAMES_MAPPING: Dict[TlsVersionEnum, Dict[str, str]] = {
    TlsVersionEnum.SSL_2_0: _SSLV2_OPENSSL_TO_RFC_NAMES_MAPPING,
    TlsVersionEnum.SSL_3_0: _TLS_OPENSSL_TO_RFC_NAMES_MAPPING,
    TlsVersionEnum.TLS_1_0: _TLS_OPENSSL_TO_RFC_NAMES_MAPPING,
    TlsVersionEnum.TLS_1_1: _TLS_OPENSSL_TO_RFC_NAMES_MAPPING,
    TlsVersionEnum.TLS_1_2: _TLS_OPENSSL_TO_RFC_NAMES_MAPPING,
}


_RFC_NAME_TO_KEY_SIZE_MAPPING: Dict[str, int] = {
    "TLS_RSA_WITH_NULL_MD5": 0,
    "TLS_RSA_WITH_NULL_SHA": 0,
    "TLS_RSA_WITH_AES_128_CBC_SHA": 128,
    "TLS_DHE_DSS_WITH_AES_128_CBC_SHA": 128,
    "TLS_DHE_RSA_WITH_AES_128_CBC_SHA": 128,
    "TLS_DH_anon_WITH_AES_128_CBC_SHA": 128,
    "TLS_RSA_WITH_AES_256_CBC_SHA": 256,
    "TLS_DHE_DSS_WITH_AES_256_CBC_SHA": 256,
    "TLS_DHE_RSA_WITH_AES_256_CBC_SHA": 256,
    "TLS_DH_anon_WITH_AES_256_CBC_SHA": 256,
    "TLS_RSA_WITH_NULL_SHA256": 0,
    "TLS_RSA_WITH_AES_128_CBC_SHA256": 128,
    "TLS_RSA_WITH_AES_256_CBC_SHA256": 256,
    "TLS_DHE_DSS_WITH_AES_128_CBC_SHA256": 128,
    "TLS_RSA_WITH_CAMELLIA_128_CBC_SHA": 128,
    "TLS_DHE_DSS_WITH_CAMELLIA_128_CBC_SHA": 128,
    "TLS_DHE_RSA_WITH_CAMELLIA_128_CBC_SHA": 128,
    "TLS_DH_anon_WITH_CAMELLIA_128_CBC_SHA": 128,
    "TLS_DHE_RSA_WITH_AES_128_CBC_SHA256": 128,
    "TLS_DHE_DSS_WITH_AES_256_CBC_SHA256": 256,
    "TLS_DHE_RSA_WITH_AES_256_CBC_SHA256": 256,
    "TLS_DH_anon_WITH_AES_128_CBC_SHA256": 128,
    "TLS_DH_anon_WITH_AES_256_CBC_SHA256": 256,
    "TLS_RSA_WITH_CAMELLIA_256_CBC_SHA": 256,
    "TLS_DHE_DSS_WITH_CAMELLIA_256_CBC_SHA": 256,
    "TLS_DHE_RSA_WITH_CAMELLIA_256_CBC_SHA": 256,
    "TLS_DH_anon_WITH_CAMELLIA_256_CBC_SHA": 256,
    "TLS_PSK_WITH_AES_128_CBC_SHA": 128,
    "TLS_PSK_WITH_AES_256_CBC_SHA": 256,
    "TLS_RSA_PSK_WITH_AES_128_CBC_SHA": 128,
    "TLS_RSA_PSK_WITH_AES_256_CBC_SHA": 256,
    "TLS_RSA_WITH_SEED_CBC_SHA": 128,
    "TLS_DHE_DSS_WITH_SEED_CBC_SHA": 128,
    "TLS_DHE_RSA_WITH_SEED_CBC_SHA": 128,
    "TLS_DH_anon_WITH_SEED_CBC_SHA": 128,
    "TLS_RSA_WITH_AES_128_GCM_SHA256": 128,
    "TLS_RSA_WITH_AES_256_GCM_SHA384": 256,
    "TLS_DHE_RSA_WITH_AES_128_GCM_SHA256": 128,
    "TLS_DHE_RSA_WITH_AES_256_GCM_SHA384": 256,
    "TLS_DHE_DSS_WITH_AES_128_GCM_SHA256": 128,
    "TLS_DHE_DSS_WITH_AES_256_GCM_SHA384": 256,
    "TLS_DH_anon_WITH_AES_128_GCM_SHA256": 128,
    "TLS_DH_anon_WITH_AES_256_GCM_SHA384": 256,
    "TLS_RSA_WITH_CAMELLIA_128_CBC_SHA256": 128,
    "TLS_DHE_DSS_WITH_CAMELLIA_128_CBC_SHA256": 128,
    "TLS_DHE_RSA_WITH_CAMELLIA_128_CBC_SHA256": 128,
    "TLS_DH_anon_WITH_CAMELLIA_128_CBC_SHA256": 128,
    "TLS_RSA_WITH_CAMELLIA_256_CBC_SHA256": 256,
    "TLS_DHE_DSS_WITH_CAMELLIA_256_CBC_SHA256": 256,
    "TLS_DHE_RSA_WITH_CAMELLIA_256_CBC_SHA256": 256,
    "TLS_DH_anon_WITH_CAMELLIA_256_CBC_SHA256": 256,
    "TLS_ECDHE_ECDSA_WITH_NULL_SHA": 0,
    "TLS_ECDHE_ECDSA_WITH_AES_128_CBC_SHA": 128,
    "TLS_ECDHE_ECDSA_WITH_AES_256_CBC_SHA": 256,
    "TLS_ECDHE_RSA_WITH_NULL_SHA": 0,
    "TLS_ECDHE_RSA_WITH_AES_128_CBC_SHA": 128,
    "TLS_ECDHE_RSA_WITH_AES_256_CBC_SHA": 256,
    "TLS_ECDH_anon_WITH_NULL_SHA": 0,
    "TLS_ECDH_anon_WITH_AES_128_CBC_SHA": 128,
    "TLS_ECDH_anon_WITH_AES_256_CBC_SHA": 256,
    "TLS_SRP_SHA_WITH_AES_128_CBC_SHA": 128,
    "TLS_SRP_SHA_RSA_WITH_AES_128_CBC_SHA": 128,
    "TLS_SRP_SHA_DSS_WITH_AES_128_CBC_SHA": 128,
    "TLS_SRP_SHA_WITH_AES_256_CBC_SHA": 256,
    "TLS_SRP_SHA_RSA_WITH_AES_256_CBC_SHA": 256,
    "TLS_SRP_SHA_DSS_WITH_AES_256_CBC_SHA": 256,
    "TLS_ECDHE_ECDSA_WITH_AES_128_CBC_SHA256": 128,
    "TLS_ECDHE_ECDSA_WITH_AES_256_CBC_SHA384": 256,
    "TLS_ECDHE_RSA_WITH_AES_128_CBC_SHA256": 128,
    "TLS_ECDHE_RSA_WITH_AES_256_CBC_SHA384": 256,
    "TLS_ECDHE_ECDSA_WITH_AES_128_GCM_SHA256": 128,
    "TLS_ECDHE_ECDSA_WITH_AES_256_GCM_SHA384": 256,
    "TLS_ECDHE_RSA_WITH_AES_128_GCM_SHA256": 128,
    "TLS_ECDHE_RSA_WITH_AES_256_GCM_SHA384": 256,
    "TLS_ECDHE_ECDSA_WITH_CAMELLIA_128_CBC_SHA256": 128,
    "TLS_ECDHE_ECDSA_WITH_CAMELLIA_256_CBC_SHA384": 256,
    "TLS_ECDHE_RSA_WITH_CAMELLIA_128_CBC_SHA256": 128,
    "TLS_ECDHE_RSA_WITH_CAMELLIA_256_CBC_SHA384": 256,
    "TLS_ECDHE_RSA_WITH_CHACHA20_POLY1305_SHA256": 256,
    "TLS_ECDHE_ECDSA_WITH_CHACHA20_POLY1305_SHA256": 256,
    "TLS_DHE_RSA_WITH_CHACHA20_POLY1305_SHA256": 256,
    "RSA_WITH_AES_128_CCM": 128,
    "RSA_WITH_AES_256_CCM": 256,
    "DHE_RSA_WITH_AES_128_CCM": 128,
    "TLS_DHE_RSA_WITH_AES_256_CCM": 256,
    "RSA_WITH_AES_128_CCM_8": 128,
    "RSA_WITH_AES_256_CCM_8": 256,
    "DHE_RSA_WITH_AES_128_CCM_8": 128,
    "DHE_RSA_WITH_AES_256_CCM_8": 256,
    "ECDHE_ECDSA_WITH_AES_128_CCM": 128,
    "ECDHE_ECDSA_WITH_AES_256_CCM": 256,
    "ECDHE_ECDSA_WITH_AES_128_CCM_8": 128,
    "ECDHE_ECDSA_WITH_AES_256_CCM_8": 256,
    "TLS_RSA_WITH_RC4_128_SHA": 128,
    "TLS_RSA_WITH_IDEA_CBC_SHA": 128,
    "TLS_RSA_EXPORT_WITH_DES40_CBC_SHA": 40,
    "TLS_RSA_WITH_DES_CBC_SHA": 56,
    "TLS_RSA_WITH_3DES_EDE_CBC_SHA": 168,
    "TLS_DH_DSS_WITH_DES_CBC_SHA": 56,
    "TLS_DH_DSS_WITH_3DES_EDE_CBC_SHA": 168,
    "TLS_DH_RSA_WITH_DES_CBC_SHA": 56,
    "TLS_DH_RSA_WITH_3DES_EDE_CBC_SHA": 168,
    "TLS_DHE_DSS_EXPORT_WITH_DES40_CBC_SHA": 40,
    "TLS_DHE_DSS_WITH_DES_CBC_SHA": 56,
    "TLS_DHE_DSS_WITH_3DES_EDE_CBC_SHA": 168,
    "TLS_DHE_RSA_EXPORT_WITH_DES40_CBC_SHA": 40,
    "TLS_DHE_RSA_WITH_DES_CBC_SHA": 56,
    "TLS_DHE_RSA_WITH_3DES_EDE_CBC_SHA": 168,
    "TLS_DH_anon_EXPORT_WITH_RC4_40_MD5": 40,
    "TLS_DH_anon_WITH_RC4_128_MD5": 128,
    "TLS_DH_anon_EXPORT_WITH_DES40_CBC_SHA": 40,
    "TLS_DH_anon_WITH_DES_CBC_SHA": 56,
    "TLS_DH_anon_WITH_3DES_EDE_CBC_SHA": 168,
    "TLS_DH_DSS_WITH_AES_128_CBC_SHA": 128,
    "TLS_DH_RSA_WITH_AES_128_CBC_SHA": 128,
    "TLS_DH_DSS_WITH_AES_256_CBC_SHA": 256,
    "TLS_DH_RSA_WITH_AES_256_CBC_SHA": 256,
    "TLS_DH_DSS_WITH_AES_128_CBC_SHA256": 128,
    "TLS_DH_RSA_WITH_AES_128_CBC_SHA256": 128,
    "TLS_DH_DSS_WITH_CAMELLIA_128_CBC_SHA": 128,
    "TLS_DH_RSA_WITH_CAMELLIA_128_CBC_SHA": 128,
    "TLS_DH_DSS_WITH_AES_256_CBC_SHA256": 256,
    "TLS_DH_RSA_WITH_AES_256_CBC_SHA256": 256,
    "TLS_DH_DSS_WITH_CAMELLIA_256_CBC_SHA": 256,
    "TLS_DH_RSA_WITH_CAMELLIA_256_CBC_SHA": 256,
    "TLS_PSK_WITH_RC4_128_SHA": 128,
    "TLS_PSK_WITH_3DES_EDE_CBC_SHA": 168,
    "TLS_DH_DSS_WITH_SEED_CBC_SHA": 128,
    "TLS_DH_RSA_WITH_SEED_CBC_SHA": 128,
    "TLS_DH_RSA_WITH_AES_128_GCM_SHA256": 128,
    "TLS_DH_RSA_WITH_AES_256_GCM_SHA384": 256,
    "TLS_DH_DSS_WITH_AES_128_GCM_SHA256": 128,
    "TLS_DH_DSS_WITH_AES_256_GCM_SHA384": 256,
    "TLS_ECDH_ECDSA_WITH_NULL_SHA": 0,
    "TLS_ECDH_ECDSA_WITH_RC4_128_SHA": 128,
    "TLS_ECDH_ECDSA_WITH_3DES_EDE_CBC_SHA": 168,
    "TLS_ECDH_ECDSA_WITH_AES_128_CBC_SHA": 128,
    "TLS_ECDH_ECDSA_WITH_AES_256_CBC_SHA": 256,
    "TLS_ECDHE_ECDSA_WITH_RC4_128_SHA": 128,
    "TLS_ECDHE_ECDSA_WITH_3DES_EDE_CBC_SHA": 168,
    "TLS_ECDH_RSA_WITH_NULL_SHA": 0,
    "TLS_ECDH_RSA_WITH_RC4_128_SHA": 128,
    "TLS_ECDH_RSA_WITH_3DES_EDE_CBC_SHA": 168,
    "TLS_ECDH_RSA_WITH_AES_128_CBC_SHA": 128,
    "TLS_ECDH_RSA_WITH_AES_256_CBC_SHA": 256,
    "TLS_ECDHE_RSA_WITH_RC4_128_SHA": 128,
    "TLS_ECDHE_RSA_WITH_3DES_EDE_CBC_SHA": 168,
    "TLS_ECDH_anon_WITH_RC4_128_SHA": 128,
    "TLS_ECDH_anon_WITH_3DES_EDE_CBC_SHA": 168,
    "TLS_SRP_SHA_WITH_3DES_EDE_CBC_SHA": 168,
    "TLS_SRP_SHA_RSA_WITH_3DES_EDE_CBC_SHA": 168,
    "TLS_SRP_SHA_DSS_WITH_3DES_EDE_CBC_SHA": 168,
    "TLS_ECDH_ECDSA_WITH_AES_128_CBC_SHA256": 128,
    "TLS_ECDH_ECDSA_WITH_AES_256_CBC_SHA384": 256,
    "TLS_ECDH_RSA_WITH_AES_128_CBC_SHA256": 128,
    "TLS_ECDH_RSA_WITH_AES_256_CBC_SHA384": 256,
    "TLS_ECDH_ECDSA_WITH_AES_128_GCM_SHA256": 128,
    "TLS_ECDH_ECDSA_WITH_AES_256_GCM_SHA384": 256,
    "TLS_ECDH_RSA_WITH_AES_128_GCM_SHA256": 128,
    "TLS_ECDH_RSA_WITH_AES_256_GCM_SHA384": 256,
    "TLS_RSA_EXPORT_WITH_RC4_40_MD5": 40,
    "TLS_RSA_WITH_RC4_128_MD5": 128,
    "TLS_RSA_EXPORT_WITH_RC2_CBC_40_MD5": 40,
    "TLS_DH_DSS_EXPORT_WITH_DES40_CBC_SHA": 40,
    "TLS_DH_RSA_EXPORT_WITH_DES40_CBC_SHA": 40,
    "TLS_KRB5_WITH_RC4_128_SHA": 128,
    "TLS_KRB5_WITH_RC4_128_MD5": 128,
    "TLS_KRB5_EXPORT_WITH_DES_CBC_40_SHA": 40,
    "TLS_KRB5_EXPORT_WITH_RC2_CBC_40_SHA": 40,
    "TLS_KRB5_EXPORT_WITH_RC4_40_SHA": 40,
    "TLS_KRB5_EXPORT_WITH_DES_CBC_40_MD5": 40,
    "TLS_KRB5_EXPORT_WITH_RC2_CBC_40_MD5": 40,
    "TLS_KRB5_EXPORT_WITH_RC4_40_MD5": 40,
    "TLS_RSA_EXPORT1024_WITH_RC4_56_SHA": 56,
    "TLS_RSA_EXPORT1024_WITH_RC4_56_MD5": 56,
    "TLS_RSA_EXPORT1024_WITH_RC2_CBC_56_MD5": 56,
    "TLS_DHE_DSS_EXPORT1024_WITH_RC4_56_SHA": 56,
    "TLS_DHE_DSS_WITH_RC4_128_SHA": 128,
    "TLS_RSA_PSK_WITH_RC4_128_SHA": 128,
    "TLS_DH_DSS_WITH_CAMELLIA_128_CBC_SHA256": 128,
    "TLS_DH_RSA_WITH_CAMELLIA_128_CBC_SHA256": 128,
    "TLS_DH_DSS_WITH_CAMELLIA_256_CBC_SHA256": 256,
    "TLS_DH_RSA_WITH_CAMELLIA_256_CBC_SHA256": 256,
    "TLS_ECDH_ECDSA_WITH_CAMELLIA_128_CBC_SHA256": 128,
    "TLS_ECDH_ECDSA_WITH_CAMELLIA_256_CBC_SHA384": 256,
    "TLS_ECDH_RSA_WITH_CAMELLIA_128_CBC_SHA256": 128,
    "TLS_ECDH_RSA_WITH_CAMELLIA_256_CBC_SHA384": 256,
    "OLD_TLS_ECDHE_RSA_WITH_CHACHA20_POLY1305_SHA256": 256,
    "OLD_TLS_ECDHE_ECDSA_WITH_CHACHA20_POLY1305_SHA256": 256,
    "OLD_TLS_DHE_RSA_WITH_CHACHA20_POLY1305_SHA256": 256,
    "TLS_KRB5_WITH_DES_CBC_SHA": 56,
    "TLS_KRB5_WITH_3DES_EDE_CBC_SHA": 168,
    "TLS_KRB5_WITH_IDEA_CBC_SHA": 128,
    "TLS_KRB5_WITH_DES_CBC_MD5": 56,
    "TLS_KRB5_WITH_3DES_EDE_CBC_MD5": 168,
    "TLS_KRB5_WITH_IDEA_CBC_MD5": 128,
    "TLS_RSA_EXPORT1024_WITH_DES_CBC_SHA": 56,
    "TLS_DHE_DSS_EXPORT1024_WITH_DES_CBC_SHA": 56,
    "TLS_GOSTR341094_WITH_28147_CNT_IMIT": 256,
    "TLS_GOSTR341001_WITH_28147_CNT_IMIT": 256,
    "TLS_RSA_PSK_WITH_3DES_EDE_CBC_SHA": 168,
    "TLS_AES_256_GCM_SHA384": 256,
    "TLS_CHACHA20_POLY1305_SHA256": 256,
    "TLS_AES_128_GCM_SHA256": 128,
    "TLS_ECDHE_ECDSA_WITH_ARIA_256_GCM_SHA384": 256,
    "TLS_ECDHE_RSA_WITH_ARIA_256_GCM_SHA384": 256,
    "TLS_DHE_DSS_WITH_ARIA_256_GCM_SHA384": 256,
    "TLS_DHE_RSA_WITH_ARIA_256_GCM_SHA384": 256,
    "TLS_ECDHE_ECDSA_WITH_ARIA_128_GCM_SHA256": 128,
    "TLS_ECDHE_RSA_WITH_ARIA_128_GCM_SHA256": 128,
    "TLS_DHE_DSS_WITH_ARIA_128_GCM_SHA256": 128,
    "TLS_DHE_RSA_WITH_ARIA_128_GCM_SHA256": 256,
    "TLS_RSA_WITH_ARIA_256_GCM_SHA384": 256,
    "TLS_RSA_WITH_ARIA_128_GCM_SHA256": 128,
    "TLS_RSA_WITH_AES_256_CCM": 256,
    "TLS_ECDHE_ECDSA_WITH_AES_128_CCM": 128,
    "TLS_DHE_RSA_WITH_AES_128_CCM": 128,
    "TLS_RSA_WITH_AES_128_CCM": 128,
    "TLS_RSA_WITH_AES_256_CCM_8": 128,
    "TLS_ECDHE_ECDSA_WITH_AES_256_CCM": 256,
    "TLS_ECDHE_ECDSA_WITH_AES_256_CCM_8": 256,
    "TLS_DHE_RSA_WITH_AES_128_CCM_8": 128,
    "TLS_DHE_RSA_WITH_AES_256_CCM_8": 256,
    "TLS_RSA_WITH_AES_128_CCM_8": 128,
    "TLS_ECDHE_ECDSA_WITH_AES_128_CCM_8": 128,
    "TLS_AES_128_CCM_8_SHA256": 128,
    "TLS_AES_128_CCM_SHA256": 128,
    "SSL_CK_RC4_128_WITH_MD5": 128,
    "SSL_CK_RC4_128_EXPORT40_WITH_MD5": 40,
    "SSL_CK_RC2_128_CBC_WITH_MD5": 128,
    "SSL_CK_RC2_128_CBC_EXPORT40_WITH_MD5": 40,
    "SSL_CK_IDEA_128_CBC_WITH_MD5": 128,
    "SSL_CK_DES_64_CBC_WITH_MD5": 56,
    "SSL_CK_DES_192_EDE3_CBC_WITH_MD5": 168,
    "SSL_CK_RC4_64_WITH_MD5": 64,
}


# TLS 1.3 cipher suites implemented in OpenSSL 1.1.1
_TLS_1_3_CIPHER_SUITES = [
    "TLS_AES_128_GCM_SHA256",
    "TLS_AES_128_CCM_SHA256",
    "TLS_AES_256_GCM_SHA384",
    "TLS_AES_128_CCM_8_SHA256",
    "TLS_CHACHA20_POLY1305_SHA256",
]


def _parse_all_cipher_suites_with_legacy_openssl(tls_version: TlsVersionEnum) -> Set[str]:
    ssl_client = LegacySslClient(ssl_version=OpenSslVersionEnum(tls_version.value))
    # Disable SRP and PSK cipher suites as they need a special setup in the client and are never used
    ssl_client.set_cipher_list("ALL:COMPLEMENTOFALL:-PSK:-SRP")
    return set(ssl_client.get_cipher_list())


def _parse_all_cipher_suites() -> Dict[TlsVersionEnum, Set[CipherSuite]]:
    tls_version_to_cipher_suites: Dict[TlsVersionEnum, Set[CipherSuite]] = {}

    for tls_version in [
        TlsVersionEnum.SSL_2_0,
        TlsVersionEnum.SSL_3_0,
        TlsVersionEnum.TLS_1_0,
        TlsVersionEnum.TLS_1_1,
    ]:
        openssl_cipher_strings = _parse_all_cipher_suites_with_legacy_openssl(tls_version)
        tls_version_to_cipher_suites[tls_version] = set()
        for cipher_suite_openssl_name in openssl_cipher_strings:
            cipher_suite_rfc_name = _OPENSSL_TO_RFC_NAMES_MAPPING[tls_version][cipher_suite_openssl_name]
            tls_version_to_cipher_suites[tls_version].add(
                CipherSuite(
                    name=cipher_suite_rfc_name,
                    openssl_name=cipher_suite_openssl_name,
                    is_anonymous=True if "anon" in cipher_suite_rfc_name else False,
                    key_size=_RFC_NAME_TO_KEY_SIZE_MAPPING[cipher_suite_rfc_name],
                )
            )

        # For TLS 1.2, we have to use both the legacy and modern OpenSSL to cover all cipher suites
        cipher_suites_from_legacy_openssl = _parse_all_cipher_suites_with_legacy_openssl(TlsVersionEnum.TLS_1_2)

        ssl_client_modern = SslClient(ssl_version=OpenSslVersionEnum(TlsVersionEnum.TLS_1_2.value))
        ssl_client_modern.set_cipher_list("ALL:COMPLEMENTOFALL:-PSK:-SRP")
        cipher_suites_from_modern_openssl = set(ssl_client_modern.get_cipher_list())

        # Combine the two sets of cipher suites
        openssl_cipher_strings = cipher_suites_from_legacy_openssl.union(cipher_suites_from_modern_openssl)
        tls_version_to_cipher_suites[TlsVersionEnum.TLS_1_2] = set()
        for cipher_suite_openssl_name in openssl_cipher_strings:
            # Ignore TLS 1.3 cipher suites
            if cipher_suite_openssl_name in _TLS_1_3_CIPHER_SUITES:
                continue

            cipher_suite_rfc_name = _OPENSSL_TO_RFC_NAMES_MAPPING[TlsVersionEnum.TLS_1_2][cipher_suite_openssl_name]
            tls_version_to_cipher_suites[TlsVersionEnum.TLS_1_2].add(
                CipherSuite(
                    name=cipher_suite_rfc_name,
                    openssl_name=cipher_suite_openssl_name,
                    is_anonymous=True if "anon" in cipher_suite_rfc_name else False,
                    key_size=_RFC_NAME_TO_KEY_SIZE_MAPPING[cipher_suite_rfc_name],
                )
            )

        # TLS 1.3 - the list is just hardcoded
        tls_version_to_cipher_suites[TlsVersionEnum.TLS_1_3] = {
            CipherSuite(
                # For TLS 1.3 OpenSSL started using the official names
                name=cipher_suite_name,
                openssl_name=cipher_suite_name,
                is_anonymous=False,
                key_size=_RFC_NAME_TO_KEY_SIZE_MAPPING[cipher_suite_name],
            )
            for cipher_suite_name in _TLS_1_3_CIPHER_SUITES
        }

    return tls_version_to_cipher_suites


class CipherSuitesRepository:
    # Pre-parse all the available cipher suites
    _ALL_CIPHER_SUITES = _parse_all_cipher_suites()

    @classmethod
    def get_all_cipher_suites(cls, tls_version: TlsVersionEnum) -> Set[CipherSuite]:
        """Get the list of cipher suites supported by OpenSSL for the given SSL/TLS version.
        """
        return cls._ALL_CIPHER_SUITES[tls_version]

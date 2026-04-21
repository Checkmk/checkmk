<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
  xmlns:xs="http://www.w3.org/2001/XMLSchema" exclude-result-prefixes="xs" version="1.0">
  <xsl:output method="xml" indent="yes" encoding="UTF-8"
    cdata-section-elements="system-out system-err failure"/>
  <xsl:decimal-format decimal-separator="." grouping-separator=","/>

  <xsl:template match="testsuites">
    <testsuites>
      <xsl:for-each select="@*">
        <xsl:choose>
          <xsl:when test="name() = 'time'">
            <xsl:attribute name="time">
              <xsl:value-of select="format-number(., '#.###')"/>
            </xsl:attribute>
          </xsl:when>
          <xsl:otherwise>
            <xsl:copy-of select="."/>
          </xsl:otherwise>
        </xsl:choose>
      </xsl:for-each>
      <xsl:apply-templates select="testsuite"/>
    </testsuites>
  </xsl:template>

  <xsl:template match="testsuite">
    <testsuite>
      <xsl:if test="@name">
        <xsl:attribute name="name">
          <xsl:value-of select="@name"/>
        </xsl:attribute>
      </xsl:if>
      <xsl:if test="@tests">
        <xsl:attribute name="tests">
          <xsl:value-of select="@tests"/>
        </xsl:attribute>
      </xsl:if>
      <xsl:if test="@errors">
        <xsl:attribute name="errors">
          <xsl:value-of select="@errors"/>
        </xsl:attribute>
      </xsl:if>
      <xsl:if test="@failures">
        <xsl:attribute name="failures">
          <xsl:value-of select="@failures"/>
        </xsl:attribute>
      </xsl:if>
      <xsl:if test="@skips">
        <xsl:attribute name="skipped">
          <xsl:value-of select="@skips"/>
        </xsl:attribute>
      </xsl:if>
      <xsl:if test="@time">
        <xsl:attribute name="time">
          <xsl:value-of select="format-number(@time, '#.###')"/>
        </xsl:attribute>
      </xsl:if>

      <xsl:apply-templates select="testcase"/>
    </testsuite>
  </xsl:template>

  <xsl:template match="testcase">
    <testcase>
      <xsl:if test="@classname">
        <xsl:attribute name="classname">
          <xsl:choose>
            <xsl:when test="../../@name = 'vitest tests'">
              <xsl:value-of select="@classname"/>
            </xsl:when>
            <xsl:otherwise>
              <xsl:value-of select="../@name"/><xsl:text>.</xsl:text><xsl:value-of select="@classname"/>
            </xsl:otherwise>
          </xsl:choose>
        </xsl:attribute>
      </xsl:if>
      <xsl:if test="@name">
        <xsl:attribute name="name">
          <xsl:value-of select="@name"/>
        </xsl:attribute>
      </xsl:if>
      <xsl:if test="@time">
        <xsl:attribute name="time">
          <xsl:value-of select="format-number(@time, '#.###')"/>
        </xsl:attribute>
      </xsl:if>
      <xsl:if test="failure">
        <xsl:choose>
          <xsl:when test="../../@name = 'vitest tests'">
            <failure>
              <xsl:value-of select="failure"/>
            </failure>
          </xsl:when>
          <xsl:otherwise>
            <xsl:copy-of select="failure"/>
          </xsl:otherwise>
        </xsl:choose>
      </xsl:if>
      <xsl:for-each select="error">
        <error>
          <xsl:attribute name="message">
            <xsl:choose>
              <xsl:when test="../../system-out">
                <xsl:value-of select="../../system-out"/>
              </xsl:when>
              <xsl:otherwise>
                <xsl:value-of select="@message"/>
              </xsl:otherwise>
            </xsl:choose>
          </xsl:attribute>
          <xsl:if test="@type">
            <xsl:attribute name="type"><xsl:value-of select="@type"/></xsl:attribute>
          </xsl:if>
          <xsl:value-of select="."/>
        </error>
      </xsl:for-each>
    </testcase>
  </xsl:template>

</xsl:stylesheet>

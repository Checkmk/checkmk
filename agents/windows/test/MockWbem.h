#include <winsock2.h>
#include <wbemcli.h>
#include "gmock/gmock.h"

using namespace ::testing;

class MockIWbemClassObject : public IWbemClassObject {
public:
    MOCK_METHOD1(GetQualifierSet,
                 HRESULT STDMETHODCALLTYPE(IWbemQualifierSet **ppQualSet));
    MOCK_METHOD5(Get, HRESULT STDMETHODCALLTYPE(LPCWSTR wszName, LONG lFlags,
                                                VARIANT *pVal, CIMTYPE *pType,
                                                LONG *plFlavor));
    MOCK_METHOD4(Put, HRESULT STDMETHODCALLTYPE(LPCWSTR wszName, LONG lFlags,
                                                VARIANT *pVal, CIMTYPE Type));
    MOCK_METHOD1(Delete, HRESULT STDMETHODCALLTYPE(LPCWSTR wszName));
    MOCK_METHOD4(GetNames,
                 HRESULT STDMETHODCALLTYPE(LPCWSTR wszQualifierName,
                                           LONG lFlags, VARIANT *pQualifierVal,
                                           SAFEARRAY **pNames));
    MOCK_METHOD1(BeginEnumeration, HRESULT STDMETHODCALLTYPE(LONG lEnumFlags));
    MOCK_METHOD5(Next, HRESULT STDMETHODCALLTYPE(LONG lFlags, BSTR *strName,
                                                 VARIANT *pVal, CIMTYPE *pType,
                                                 LONG *plFlavor));
    MOCK_METHOD0(EndEnumeration, HRESULT STDMETHODCALLTYPE());
    MOCK_METHOD2(GetPropertyQualifierSet,
                 HRESULT STDMETHODCALLTYPE(LPCWSTR wszProperty,
                                           IWbemQualifierSet **ppQualSet));
    MOCK_METHOD1(Clone, HRESULT STDMETHODCALLTYPE(IWbemClassObject **ppCopy));
    MOCK_METHOD2(GetObjectText,
                 HRESULT STDMETHODCALLTYPE(LONG lFlags, BSTR *pstrObjectText));
    MOCK_METHOD2(SpawnDerivedClass,
                 HRESULT STDMETHODCALLTYPE(LONG lFlags,
                                           IWbemClassObject **ppNewClass));
    MOCK_METHOD2(SpawnInstance,
                 HRESULT STDMETHODCALLTYPE(LONG lFlags,
                                           IWbemClassObject **ppNewInstance));
    MOCK_METHOD2(CompareTo,
                 HRESULT STDMETHODCALLTYPE(LONG lFlags,
                                           IWbemClassObject *pCompareTo));
    MOCK_METHOD2(GetPropertyOrigin,
                 HRESULT STDMETHODCALLTYPE(LPCWSTR wszName,
                                           BSTR *pstrClassName));
    MOCK_METHOD1(InheritsFrom, HRESULT STDMETHODCALLTYPE(LPCWSTR strAncestor));
    MOCK_METHOD4(GetMethod,
                 HRESULT STDMETHODCALLTYPE(LPCWSTR wszName, LONG lFlags,
                                           IWbemClassObject **ppInSignature,
                                           IWbemClassObject **ppOutSignature));
    MOCK_METHOD4(PutMethod,
                 HRESULT STDMETHODCALLTYPE(LPCWSTR wszName, LONG lFlags,
                                           IWbemClassObject *pInSignature,
                                           IWbemClassObject *pOutSignature));
    MOCK_METHOD1(DeleteMethod, HRESULT STDMETHODCALLTYPE(LPCWSTR wszName));
    MOCK_METHOD1(BeginMethodEnumeration,
                 HRESULT STDMETHODCALLTYPE(LONG lEnumFlags));
    MOCK_METHOD4(NextMethod,
                 HRESULT STDMETHODCALLTYPE(LONG lFlags, BSTR *pstrName,
                                           IWbemClassObject **ppInSignature,
                                           IWbemClassObject **ppOutSignature));
    MOCK_METHOD0(EndMethodEnumeration, HRESULT STDMETHODCALLTYPE());
    MOCK_METHOD2(GetMethodQualifierSet,
                 HRESULT STDMETHODCALLTYPE(LPCWSTR wszMethod,
                                           IWbemQualifierSet **ppQualSet));
    MOCK_METHOD2(GetMethodOrigin,
                 HRESULT STDMETHODCALLTYPE(LPCWSTR wszMethodName,
                                           BSTR *pstrClassName));
    MOCK_METHOD2(QueryInterface,
                 HRESULT STDMETHODCALLTYPE(REFIID riid, void **ppvObject));
    MOCK_METHOD0(AddRef, ULONG STDMETHODCALLTYPE());
    MOCK_METHOD0(Release, ULONG STDMETHODCALLTYPE());
};

class MockIEnumWbemClassObject : public IEnumWbemClassObject {
public:
    MOCK_METHOD1(Clone,
                 HRESULT STDMETHODCALLTYPE(IEnumWbemClassObject **ppEnum));
    MOCK_METHOD4(Next, HRESULT STDMETHODCALLTYPE(LONG lTimeOut, ULONG uCount,
                                                 IWbemClassObject **ppObjects,
                                                 ULONG *puReturned));
    MOCK_METHOD2(NextAsync, HRESULT STDMETHODCALLTYPE(ULONG uCount,
                                                      IWbemObjectSink *pSink));
    MOCK_METHOD0(Reset, HRESULT STDMETHODCALLTYPE());
    MOCK_METHOD2(Skip, HRESULT STDMETHODCALLTYPE(LONG lTimeOut, ULONG UCount));
    MOCK_METHOD2(QueryInterface,
                 HRESULT STDMETHODCALLTYPE(REFIID riid, void **ppvObject));
    MOCK_METHOD0(AddRef, ULONG STDMETHODCALLTYPE());
    MOCK_METHOD0(Release, ULONG STDMETHODCALLTYPE());
};

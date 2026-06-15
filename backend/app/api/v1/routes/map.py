'''地图服务API路由'''
from fastapi import APIRouter, HTTPException, Query


@router.get(
    "/poi",
    response_model=POISearchResponse,
    summary="搜索POI",
    description="根据关键词搜索POI(兴趣点)"
)
async def search_poi(
    keyword: str = Query(..., description="搜索关键词",example="黄鹤楼"),
    city: str = Query(...,description="城市",example="武汉"),
    citylimit: bool = Query(True, description="是否在限制的城市里面")
):
    '''
    搜索POI

    Args:
        keywords:
    Return:
        POI搜索结果
    '''
    